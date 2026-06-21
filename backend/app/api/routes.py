from __future__ import annotations

import logging
import os
import re
import time
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from urllib.parse import urlencode

from app.api.dependencies import get_current_user, get_optional_current_user, require_admin
from app.api.v1.routes.ai_chat import router as ai_chat_router
from app.core.database import get_db
from app.core.config import settings
from app.models.entities import User
from app.services.auth_service import AuthService
from app.services.food_service import FoodService, InteractionService, UserService
from app.services.nutrition_statistics_service import NutritionStatisticsService
from app.services.ingredient_recognition_service import recognize_ingredients_from_image
from app.services.weight_log_service import WeightLogService
from app.services.gamification_service import GamificationService
from app.services.meal_reminder_service import send_test_meal_reminder_email, send_test_meal_reminder_sms
from app.services.sms_service import is_twilio_configured
from app.views.schemas import (
    AccountStatusUpdate,
    AdminCategorySummaryResponse,
    AdminFoodListResponse,
    AdminMealPlanListResponse,
    AdminOverviewResponse,
    AdminStatsResponse,
    AdminSystemErrorListResponse,
    AdminUserListResponse,
    AuthTokenResponse,
    CurrentUserView,
    FavoriteFoodListResponse,
    FavoriteFoodResponse,
    FoodCategoryCreate,
    FoodCategoryListResponse,
    FoodCategoryUpdate,
    FoodCategoryView,
    FoodCreate,
    FoodListResponse,
    FoodRatingInput,
    FoodRatingView,
    FoodUpdate,
    FoodView,
    ForgotPasswordInput,
    MealPlanItemCheckInInput,
    MealPlanRegenerateInput,
    MealPlanRestoreInput,
    MealReminderTestEmailInput,
    MealReminderTestEmailResponse,
    MealReminderTestSmsInput,
    MealReminderTestSmsResponse,
    MealConsumptionToggleInput,
    MessageResponse,
    NutritionStatisticsResponse,
    RecommendationHistoryDetail,
    RecommendationHistoryResponse,
    RecommendationInput,
    RecommendationOutput,
    EmailVerificationInput,
    RegistrationVerificationResponse,
    ResendVerificationInput,
    ResetPasswordInput,
    TodayMealPlanResponse,
    UserCreate,
    UserLogin,
    GoogleLoginInput,
    GoogleOAuthUrlResponse,
    UserProfileInput,
    UserProfileView,
    UserUpdate,
    UserView,
    WeightLogCreate,
    WeightDailyUpdateInput,
    WeightDailyUpdateResponse,
    WeightMilestoneResponse,
    WeightLogResponse,
    WeightLogSummary,
)


router = APIRouter(prefix="/api/v1")
logger = logging.getLogger(__name__)

_admin_service_import_error: Exception | None = None
try:
    from app.services.admin_service import AdminService
except Exception as exc:  # pragma: no cover - protects non-admin routes from unrelated import failures
    AdminService = None  # type: ignore[assignment]
    _admin_service_import_error = exc
    logger.exception("[ADMIN SERVICE IMPORT ERROR] %s", exc)

_recommendation_controller_import_error: Exception | None = None
try:
    from app.controllers.recommendation_controller import controller
except Exception as exc:  # pragma: no cover - protects auth routes from unrelated import failures
    controller = None
    _recommendation_controller_import_error = exc
    logger.exception("[RECOMMENDATION CONTROLLER IMPORT ERROR] %s", exc)

router.include_router(ai_chat_router)
auth_service = AuthService()
food_service = FoodService()
user_service = UserService()
interaction_service = InteractionService()
weight_log_service = WeightLogService()
nutrition_statistics_service = NutritionStatisticsService()
gamification_service = GamificationService()
admin_service = AdminService() if AdminService is not None else None


def _require_recommendation_controller():
    if controller is None:
        detail = "Recommendation service is temporarily unavailable"
        if _recommendation_controller_import_error is not None:
            detail = f"Recommendation service unavailable: {type(_recommendation_controller_import_error).__name__}"
        raise HTTPException(status_code=503, detail=detail)
    return controller


def _require_admin_service():
    if admin_service is None:
        detail = "Admin service is temporarily unavailable"
        if _admin_service_import_error is not None:
            detail = f"Admin service unavailable: {type(_admin_service_import_error).__name__}"
        raise HTTPException(status_code=503, detail=detail)
    return admin_service


def normalize_ingredient_names(items):
    result = []
    seen = set()

    for item in items or []:
        name = str(item or "").strip()
        if not name:
            continue

        key = strip_accents(name).lower()
        if key in seen:
            continue

        seen.add(key)
        result.append(name)

    return result


def strip_accents(value):
    import unicodedata

    text = "".join(
        char for char in unicodedata.normalize("NFD", value)
        if unicodedata.category(char) != "Mn"
    )
    return text.replace("đ", "d").replace("Đ", "D")


def fallback_ingredients_from_filename(filename):
    normalized_filename = normalize_filename(filename)

    filename_ingredient_aliases = {
        "Thịt heo": ["thit heo", "thit lon", "heo", "lon", "pork"],
        "Thịt gà": ["thit ga", "ga", "chicken"],
        "Thịt bò": ["thit bo", "bo", "beef"],
        "Trứng": ["trung", "egg"],
        "Cà rốt": ["ca rot", "carrot"],
        "Nấm": ["nam", "mushroom"],
        "Rau cải": ["rau cai", "cai", "rau"],
        "Sữa": ["sua", "milk"],
        "Đậu hũ": ["dau hu", "dau phu", "tofu"],
        "Cà chua": ["ca chua", "tomato"],
        "Cua": ["cua", "crab", "thit cua", "cua bien", "cua dong"],
    }

    found = []
    for ingredient, patterns in filename_ingredient_aliases.items():
        if any(pattern_in_filename(pattern, normalized_filename) for pattern in patterns):
            found.append(ingredient)

    return normalize_ingredient_names(found)


def normalize_filename(value):
    text = os.path.basename(str(value or ""))
    text = re.sub(r"\.[a-z0-9]+$", " ", text, flags=re.IGNORECASE)
    text = strip_accents(text).lower()
    text = re.sub(r"[\._\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def pattern_in_filename(pattern, normalized_filename):
    normalized_pattern = normalize_filename(pattern)
    if not normalized_pattern:
        return False
    return re.search(rf"(^|\s){re.escape(normalized_pattern)}($|\s)", normalized_filename) is not None


def _is_clip_unavailable_error(exc: Exception) -> bool:
    message = f"{type(exc).__name__}: {exc}".lower()
    return any(token in message for token in ("torch is unavailable", "no module named 'torch'", " no module named torch", "clip", "runtimeerror", "torch"))


@router.get("/health", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/debug-db", tags=["system"])
def debug_db(email: str, db: Session = Depends(get_db)) -> dict:
    from app.models.entities import User, UserProfileEntity
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"error": f"User not found: {email}"}
    profile = db.query(UserProfileEntity).filter(UserProfileEntity.user_id == user.id).first()
    return {
        "user_id": user.id,
        "email": user.email,
        "user_disliked_foods": getattr(user, "disliked_foods", "N/A"),
        "profile_disliked_foods": getattr(profile, "disliked_foods", "N/A") if profile else None,
        "profile_favorite_foods": getattr(profile, "favorite_foods", "N/A") if profile else None,
        "profile_disliked_food_groups": getattr(profile, "disliked_food_groups", "N/A") if profile else None,
    }


@router.post("/debug-db-reset", tags=["system"])
def debug_db_reset(email: str, db: Session = Depends(get_db)) -> dict:
    from app.models.entities import User, UserProfileEntity
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"error": f"User not found: {email}"}
    profile = db.query(UserProfileEntity).filter(UserProfileEntity.user_id == user.id).first()
    
    # Reset the password to password123
    import bcrypt as _bcrypt
    hashed = _bcrypt.hashpw("password123".encode("utf-8"), _bcrypt.gensalt())
    user.password_hash = "bcrypt$" + hashed.decode("utf-8")
    
    if profile:
        profile.disliked_foods = None
        profile.favorite_foods = None
        profile.disliked_food_groups = None
        
    db.commit()
    return {"status": "reset_successful"}


@router.post("/auth/register", response_model=RegistrationVerificationResponse, tags=["auth"])
def register(payload: UserCreate, db: Session = Depends(get_db)) -> RegistrationVerificationResponse:
    return auth_service.register(payload, db)


@router.post("/auth/login", response_model=AuthTokenResponse, tags=["auth"])
def login(payload: UserLogin, db: Session = Depends(get_db)) -> AuthTokenResponse:
    return auth_service.login(payload, db)


@router.post("/auth/verify-email", response_model=AuthTokenResponse, tags=["auth"])
def verify_email(payload: EmailVerificationInput, db: Session = Depends(get_db)) -> AuthTokenResponse:
    return auth_service.verify_email(payload, db)


@router.post("/auth/resend-verification", response_model=MessageResponse, tags=["auth"])
def resend_verification(payload: ResendVerificationInput, db: Session = Depends(get_db)) -> MessageResponse:
    return auth_service.resend_verification(payload, db)


@router.post("/auth/google", response_model=AuthTokenResponse, tags=["auth"])
def google_login(payload: GoogleLoginInput, db: Session = Depends(get_db)) -> AuthTokenResponse:
    """Google OAuth login endpoint with improved error handling"""
    try:
        token = payload.credential or payload.id_token or payload.access_token
        
        if not token:
            raise HTTPException(
                status_code=400,
                detail="Missing Google credential. Please provide credential, id_token, or access_token."
            )
        
        return auth_service.google_login(token, db)
    
    except HTTPException:
        # Re-raise HTTPException from auth_service (already has proper status codes)
        raise
    
    except Exception as e:
        logger.error(f"[GOOGLE LOGIN ERROR] Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Google login failed: {str(e)}"
        )


@router.get("/auth/google/url", response_model=GoogleOAuthUrlResponse, tags=["auth"])
def google_oauth_url() -> GoogleOAuthUrlResponse:
    # Log immediate hit and env snapshot to help debugging from backend terminal
    try:
        print("[GOOGLE AUTH URL HIT]")
        
        # Detailed env check
        google_client_secret_raw = os.getenv("GOOGLE_CLIENT_SECRET")
        env_snapshot = {
            "GOOGLE_CLIENT_ID_EXISTS": bool(os.getenv("GOOGLE_CLIENT_ID")),
            "GOOGLE_CLIENT_SECRET_EXISTS": bool(google_client_secret_raw),
            "GOOGLE_CLIENT_SECRET_LENGTH": len(google_client_secret_raw) if google_client_secret_raw else 0,
            "GOOGLE_CLIENT_SECRET_IS_PLACEHOLDER": google_client_secret_raw == "GOCSPX-YOUR_GOOGLE_CLIENT_SECRET_HERE",
            "GOOGLE_REDIRECT_URI": os.getenv("GOOGLE_REDIRECT_URI"),
            "FRONTEND_URL": os.getenv("FRONTEND_URL") or settings.frontend_url,
            "BACKEND_URL": os.getenv("BACKEND_URL") or f"{settings.app_host}:{settings.app_port}",
            "VITE_GOOGLE_CLIENT_ID": bool(os.getenv("VITE_GOOGLE_CLIENT_ID")),
            "settings.google_client_id_exists": bool(settings.google_client_id),
            "settings.google_client_secret_exists": bool(settings.google_client_secret),
            "settings.google_client_secret_is_placeholder": settings.google_client_secret == "GOCSPX-YOUR_GOOGLE_CLIENT_SECRET_HERE",
        }
        print("[GOOGLE AUTH ENV CHECK]", env_snapshot)
        logger.info("[GOOGLE AUTH ENV CHECK] %s", env_snapshot)
        
        # If VITE_* exists but backend GOOGLE_* does not, warn the developer
        if not settings.google_client_id and os.getenv("VITE_GOOGLE_CLIENT_ID"):
            logger.warning("[GOOGLE AUTH ENV MISMATCH] backend GOOGLE_CLIENT_ID missing but VITE_GOOGLE_CLIENT_ID exists")
            print("[GOOGLE AUTH ENV MISMATCH] backend GOOGLE_CLIENT_ID missing but VITE_GOOGLE_CLIENT_ID exists")
    except Exception:
        # Make sure logging never breaks the route
        print("[GOOGLE AUTH URL ENV] failed to read env snapshot", traceback.format_exc())

    # Explicitly validate required env/config before attempting to generate URL
    missing = []
    if not settings.google_client_id:
        missing.append("GOOGLE_CLIENT_ID")
    if not settings.google_client_secret:
        missing.append("GOOGLE_CLIENT_SECRET")
    elif settings.google_client_secret == "GOCSPX-YOUR_GOOGLE_CLIENT_SECRET_HERE":
        missing.append("GOOGLE_CLIENT_SECRET (still using placeholder)")
    if not settings.google_redirect_uri:
        missing.append("GOOGLE_REDIRECT_URI")

    if missing:
        logger.error("[GET /api/v1/auth/google/url MISSING CONFIG] %s", missing)
        print("[GET /api/v1/auth/google/url MISSING CONFIG]", missing)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Google OAuth configuration is missing or incomplete",
                "missing": missing,
            },
        )

    try:
        url = auth_service.get_google_oauth_url()
        logger.info("[GET /api/v1/auth/google/url] generated oauth url")
        print("[GET /api/v1/auth/google/url] generated oauth url successfully")
        return JSONResponse(status_code=200, content={"success": True, "url": url})
    except HTTPException as exc:
        logger.error("[GET /api/v1/auth/google/url ERROR] %s", exc.detail)
        print("[GET /api/v1/auth/google/url ERROR]", exc)
        print("[GET /api/v1/auth/google/url ERROR DETAIL]", exc.detail)
        return JSONResponse(status_code=exc.status_code or 500, content={"success": False, "message": str(exc.detail)})
    except Exception as exc:
        logger.exception("[GET /api/v1/auth/google/url ERROR] unexpected: %s", exc)
        print("[GET /api/v1/auth/google/url ERROR]", exc)
        print("[GET /api/v1/auth/google/url ERROR MESSAGE]", str(exc))
        print("[GET /api/v1/auth/google/url ERROR TRACEBACK]")
        print(traceback.format_exc())
        return JSONResponse(status_code=500, content={"success": False, "message": str(exc) or "Google OAuth URL generation failed"})


@router.get("/auth/google/callback", tags=["auth"])
def google_oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    frontend_url = settings.frontend_url.rstrip("/")
    if error:
        logger.warning("[GOOGLE OAUTH CALLBACK ERROR] error=%s desc=%s", error, error_description or "")
        query = urlencode({"google_error": error_description or error})
        return RedirectResponse(url=f"{frontend_url}/login?{query}", status_code=302)

    try:
        token_response = auth_service.google_oauth_callback(code, state, db)
    except HTTPException as exc:
        logger.warning("[GOOGLE OAUTH CALLBACK FAILED] status=%s detail=%s", exc.status_code, str(exc.detail)[:240])
        query = urlencode({"google_error": "google_oauth_failed"})
        return RedirectResponse(url=f"{frontend_url}/login?{query}", status_code=302)
    except Exception as exc:
        logger.exception("[GOOGLE OAUTH CALLBACK FAILED] unexpected_error=%s", type(exc).__name__)
        query = urlencode({"google_error": "google_oauth_failed"})
        return RedirectResponse(url=f"{frontend_url}/login?{query}", status_code=302)

    query = urlencode({"token": token_response.access_token})
    return RedirectResponse(url=f"{frontend_url}/login?{query}", status_code=302)


@router.post("/auth/forgot-password", response_model=MessageResponse, tags=["auth"])
def forgot_password(payload: ForgotPasswordInput, db: Session = Depends(get_db)) -> MessageResponse:
    return MessageResponse(**auth_service.forgot_password(payload, db))


@router.post("/auth/reset-password", response_model=MessageResponse, tags=["auth"])
def reset_password(payload: ResetPasswordInput, db: Session = Depends(get_db)) -> MessageResponse:
    return MessageResponse(**auth_service.reset_password(payload, db))


@router.get("/users/me", tags=["users"])
def get_me(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> object:
    """Return current user info, or 401/unauthenticated without crashing when session missing."""
    try:
        if current_user is None:
            # Not authenticated — return a clear 401 response
            logger.info("[GET /api/v1/users/me] unauthenticated request")
            return JSONResponse(status_code=401, content={"success": False, "message": "Unauthenticated"})
        return user_service.get_me(db, current_user)
    except Exception as exc:
        # Log the full error and return a 500 with detail for debugging
        logger.exception("[GET /api/v1/users/me ERROR] %s", exc)
        print("[GET /api/v1/users/me ERROR]", exc)
        return JSONResponse(status_code=500, content={"success": False, "message": "Server error retrieving user"})


@router.put("/users/me", response_model=CurrentUserView, tags=["users"])
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CurrentUserView:
    return user_service.update_me(db, current_user, payload)


@router.put("/users/me/profile", response_model=UserProfileView, tags=["users"])
def update_profile(
    payload: UserProfileInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileView:
    return user_service.update_profile(db, current_user, payload)


@router.post("/meal-reminders/test-email", response_model=MealReminderTestEmailResponse, tags=["meal-reminders"])
def test_meal_reminder_email(
    payload: MealReminderTestEmailInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MealReminderTestEmailResponse:
    success, message, sent_to = send_test_meal_reminder_email(current_user, payload.meal_type)
    return MealReminderTestEmailResponse(success=success, message=message, sent_to=sent_to)


@router.get("/sms/status", tags=["meal-reminders"])
def sms_status(
    _: User = Depends(get_current_user),
) -> dict:
    """Return whether eSMS.vn SMS is configured and ready to send."""
    from app.core.config import settings
    import os
    
    # Check if keys are loaded
    api_key_from_settings = settings.esms_api_key
    secret_key_from_settings = settings.esms_secret_key
    api_key_from_env = os.getenv("ESMS_API_KEY", "")
    secret_key_from_env = os.getenv("ESMS_SECRET_KEY", "")
    
    return {
        "configured": is_twilio_configured(),
        "debug": {
            "api_key_in_settings": bool(api_key_from_settings),
            "secret_key_in_settings": bool(secret_key_from_settings),
            "api_key_in_env": bool(api_key_from_env),
            "secret_key_in_env": bool(secret_key_from_env),
            "api_key_length": len(api_key_from_settings) if api_key_from_settings else 0,
            "secret_key_length": len(secret_key_from_settings) if secret_key_from_settings else 0,
        }
    }


@router.post("/meal-reminders/test-sms", response_model=MealReminderTestSmsResponse, tags=["meal-reminders"])
def test_meal_reminder_sms(
    payload: MealReminderTestSmsInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MealReminderTestSmsResponse:
    import logging
    logger = logging.getLogger(__name__)
    logger.info("[TEST SMS ROUTE CALLED] user_id=%s meal_type=%s", current_user.id, payload.meal_type)
    
    success, message, sent_to = send_test_meal_reminder_sms(current_user, payload.meal_type, db=db)
    
    logger.info("[TEST SMS ROUTE RESULT] success=%s message=%s", success, message)
    return MealReminderTestSmsResponse(success=success, message=message, sent_to=sent_to)


@router.post("/weight-logs", response_model=WeightLogResponse, tags=["weight-logs"])
def upsert_weight_log(
    payload: WeightLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WeightLogResponse:
    return WeightLogResponse(**weight_log_service.save_log(db, current_user, payload))


@router.post("/weight-logs/daily", response_model=WeightDailyUpdateResponse, tags=["weight-logs"])
def upsert_daily_weight_log(
    payload: WeightDailyUpdateInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WeightDailyUpdateResponse:
    return WeightDailyUpdateResponse(**weight_log_service.save_daily_log(db, current_user, payload.weight_kg))


@router.get("/weight-logs", response_model=list[WeightMilestoneResponse], tags=["weight-logs"])
def list_weight_logs(
    range: str = Query("30", pattern="^(30|90|all)$"),
    mode: str = Query("daily", pattern="^(daily|milestones|raw|all)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WeightMilestoneResponse]:
    print("[WEIGHT CURRENT USER]", {
        "endpoint": "/weight-logs",
        "user_id": current_user.id,
        "email": current_user.email,
    })
    range_days = None if range == "all" else int(range)
    return [WeightMilestoneResponse(**item) for item in weight_log_service.list_logs(db, current_user, range_days, mode=mode)]


@router.get("/weight-logs/raw", response_model=list[WeightLogResponse], tags=["weight-logs"])
def list_raw_weight_logs(
    range: str = Query("30", pattern="^(30|90|all)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WeightLogResponse]:
    range_days = None if range == "all" else int(range)
    return [WeightLogResponse(**item) for item in weight_log_service.list_logs(db, current_user, range_days, mode="raw")]


@router.get("/weight-logs/summary", response_model=WeightLogSummary, tags=["weight-logs"])
def weight_log_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WeightLogSummary:
    print("[WEIGHT SUMMARY API USER]", {
        "endpoint": "/weight-logs/summary",
        "user_id": current_user.id,
        "email": current_user.email,
    })
    return WeightLogSummary(**weight_log_service.summary(db, current_user))


@router.get("/foods", response_model=FoodListResponse, tags=["foods"])
def list_foods(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> FoodListResponse:
    return FoodListResponse(**food_service.list_foods(db, q, category, limit, offset))


@router.post("/ingredients/candidates", tags=["foods"])
def ingredient_candidates(
    payload: dict,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """Return candidate foods for given ingredient names (for frontend validation/debug)."""
    try:
        ingredients = payload.get("ingredients") if isinstance(payload, dict) else None
        limit = int(payload.get("limit", 10)) if isinstance(payload, dict) else 10
        if not ingredients or not isinstance(ingredients, (list, tuple)):
            return {"candidatesByIngredient": {}, "candidateCounts": {}}
        # Use the recommender utility functions to inspect raw DB matches
        from app.services.recommender_service import debug_raw_ingredient_matches

        recommender = None
        try:
            # Build a recommender to get access to raw_df via helper
            from app.services.recommender_service import RecommenderService
            recommender = RecommenderService._build_recommender_from_sql(db)
            all_foods = recommender.raw_df if getattr(recommender, "raw_df", None) is not None else None
        except Exception:
            all_foods = None

        results: dict[str, list[dict]] = {}
        counts: dict[str, int] = {}
        for ing in ingredients:
            try:
                rows = debug_raw_ingredient_matches(all_foods or [], ing)
                counts[str(ing)] = int(len(rows))
                results[str(ing)] = rows[: int(limit)]
            except Exception:
                counts[str(ing)] = 0
                results[str(ing)] = []

        return {"candidatesByIngredient": results, "candidateCounts": counts}
    except Exception as exc:
        logger.warning("[INGREDIENT CANDIDATES API] failed: %s", exc)
        return {"candidatesByIngredient": {}, "candidateCounts": {}}

@router.get("/foods/{food_id}", response_model=FoodView, tags=["foods"])
def get_food(
    food_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> FoodView:
    return FoodView(**food_service.get_food(db, food_id))


@router.get("/users/me/favorites", response_model=FavoriteFoodListResponse, tags=["interactions"])
def list_favorites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FavoriteFoodListResponse:
    return FavoriteFoodListResponse(**interaction_service.list_favorites(db, current_user))


@router.post("/foods/{food_id}/favorite", response_model=FavoriteFoodResponse, tags=["interactions"])
def add_favorite(
    food_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FavoriteFoodResponse:
    return FavoriteFoodResponse(**interaction_service.add_favorite(db, current_user, food_id))


@router.delete("/foods/{food_id}/favorite", response_model=FavoriteFoodResponse, tags=["interactions"])
def remove_favorite(
    food_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FavoriteFoodResponse:
    return FavoriteFoodResponse(**interaction_service.remove_favorite(db, current_user, food_id))


@router.post("/foods/{food_id}/rating", response_model=FoodRatingView, tags=["interactions"])
def rate_food(
    food_id: str,
    payload: FoodRatingInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FoodRatingView:
    return FoodRatingView(**interaction_service.rate_food(db, current_user, food_id, payload))


@router.post("/recommendations", response_model=RecommendationOutput, tags=["recommendations"])
def create_recommendation(
    payload: RecommendationInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendationOutput:
    return _require_recommendation_controller().create_recommendation(payload, db, current_user)


@router.post("/meal-plans/regenerate", response_model=RecommendationOutput, tags=["meal-plans"])
def regenerate_meal_plan(
    payload: MealPlanRegenerateInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendationOutput:
    start = time.perf_counter()
    if os.getenv("DEBUG_RECOMMENDER", "false").strip().lower() in {"1", "true", "yes", "on"}:
        logger.info("[REGENERATE AVAILABLE INGREDIENTS RAW] %s", payload.available_ingredients)
    result = _require_recommendation_controller().regenerate_meal_plan(payload, db, current_user)
    logger.info(
        "[REGENERATE ROUTE TIMING] %s",
        {"total_ms": round((time.perf_counter() - start) * 1000.0, 2)},
    )
    return result


@router.post("/meal-plans/restore", response_model=TodayMealPlanResponse, tags=["meal-plans"])
def restore_meal_plan(
    payload: MealPlanRestoreInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TodayMealPlanResponse:
    return TodayMealPlanResponse(**_require_recommendation_controller().restore_meal_plan(payload, db, current_user))


@router.post("/meal-plans/recognize-ingredients", tags=["meal-plans"])
async def recognize_ingredients(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return await recognize_ingredients_from_image(file)


@router.post("/ingredients/recognize-image", tags=["ingredients"])
async def recognize_ingredient_image(
    file: UploadFile | None = File(None),
    image_url: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    try:
        print("[INGREDIENT ROUTE HIT] /api/v1/ingredients/recognize-image", flush=True)
        print("[INGREDIENT ROUTE FILE]", {
            "filename": file.filename if file else "",
            "content_type": file.content_type if file else "",
            "has_image_url": bool(image_url),
        }, flush=True)

        if not file and not image_url:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "ingredients": [],
                    "message": "Vui lòng tải lên file ảnh hoặc cung cấp URL ảnh hợp lệ.",
                },
            )

        image_bytes = None
        if file:
            content_type = (file.content_type or "").lower()
            if not content_type.startswith("image/"):
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "ingredients": [],
                        "message": "Vui lòng tải lên file ảnh hợp lệ (JPG, PNG, WEBP).",
                    },
                )

            image_bytes = await file.read()
            
            logger.info("[INGREDIENT IMAGE ROUTE INPUT] %s", {
                "filename": file.filename,
                "contentType": file.content_type,
                "bytes": len(image_bytes or b""),
            })
            
            print("[INGREDIENT ROUTE FILE BYTES]", {
                "fileSize": len(image_bytes),
                "hasBytes": bool(image_bytes),
                "firstBytes": image_bytes[:16].hex(),
            }, flush=True)
            if not image_bytes:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "ingredients": [],
                        "message": "File ảnh rỗng.",
                    },
                )

        try:
            from app.services.clip_ingredient_service import recognize_ingredients_with_clip

            raw = recognize_ingredients_with_clip(
                image_bytes=image_bytes,
                filename=file.filename if file else None,
                image_url=image_url,
            )

            if isinstance(raw, dict):
                result = raw
            elif isinstance(raw, list):
                ingredients = normalize_ingredient_names(raw)
                result = {
                    "success": bool(ingredients),
                    "ingredients": ingredients,
                    "candidates": [{"name": ingredient, "score": 0.0} for ingredient in ingredients],
                    "message": "Đã nhận diện nguyên liệu." if ingredients else "Không nhận diện được nguyên liệu trong ảnh.",
                    "usedFilenameFallback": False,
                }
            else:
                result = {
                    "success": False,
                    "ingredients": [],
                    "candidates": [],
                    "message": "Không nhận diện được nguyên liệu trong ảnh.",
                    "usedFilenameFallback": False,
                }

        except Exception as service_exc:
            print("[INGREDIENT SERVICE FAILED]", type(service_exc).__name__, repr(service_exc), flush=True)
            traceback.print_exc()
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "ingredients": [],
                    "candidates": [],
                    "message": f"Lỗi nhận diện ảnh: {type(service_exc).__name__}: {str(service_exc)}",
                },
            )

        print("[INGREDIENT RECOGNIZE RESULT]", result, flush=True)
        return result

    except Exception as exc:
        print("[INGREDIENT RECOGNIZE ERROR TYPE]", type(exc).__name__, flush=True)
        print("[INGREDIENT RECOGNIZE ERROR REPR]", repr(exc), flush=True)
        print("[INGREDIENT RECOGNIZE TRACEBACK]", flush=True)
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "ingredients": [],
                "message": f"Lỗi nhận diện ảnh: {type(exc).__name__}: {str(exc)}",
            },
        )



from datetime import date, datetime
from sqlalchemy import func, select
from app.models.entities import MealConsumptionLog, MealPlan, Meal, MealPlanItem, Food

@router.post("/meal-consumption/toggle", tags=["meal-consumption"])
def toggle_meal_consumption(
    payload: MealConsumptionToggleInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    import logging
    logger = logging.getLogger(__name__)
    try:
        app_tz = ZoneInfo(settings.app_timezone or "Asia/Ho_Chi_Minh")
    except Exception:
        app_tz = ZoneInfo("Asia/Ho_Chi_Minh")
    today = datetime.now(app_tz).date()
    meal_plan_item_id = payload.meal_plan_item_id or payload.item_id

    print("[MEAL CONSUMPTION TOGGLE REQUEST]", {
        "user_id": current_user.id,
        "meal_plan_id": payload.meal_plan_id,
        "meal_type": payload.meal_type,
        "meal_plan_item_id": meal_plan_item_id,
        "item_id": payload.item_id,
        "food_id": payload.food_id,
        "food_name": payload.food_name,
        "is_eaten": payload.is_eaten
    })

    if payload.meal_plan_id is None:
        raise HTTPException(status_code=400, detail="meal_plan_id is required")

    meal_plan = db.get(MealPlan, int(payload.meal_plan_id))
    if meal_plan is None or meal_plan.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Meal plan not found")

    meal_type = str(payload.meal_type or "").strip().lower()
    original_food_id_str = str(payload.food_id) if payload.food_id is not None else None
    food_id_str = original_food_id_str

    def resolve_meal_plan_item() -> MealPlanItem | None:
        candidate_ids: list[object] = [payload.meal_plan_item_id, payload.item_id]
        for candidate_id in candidate_ids:
            if candidate_id is None:
                continue
            try:
                candidate_item = db.get(MealPlanItem, int(candidate_id))
            except (TypeError, ValueError):
                candidate_item = None
            if candidate_item and candidate_item.meal and candidate_item.meal.meal_plan_id == meal_plan.id:
                return candidate_item

        normalized_food_id = str(payload.food_id).strip() if payload.food_id is not None else ""
        normalized_food_name = str(payload.food_name).strip().lower() if payload.food_name is not None else ""

        if not meal_type:
            return None

        for meal in meal_plan.meals:
            if str(meal.meal_type or "").strip().lower() != meal_type:
                continue
            for item in meal.items:
                if normalized_food_id and str(item.food_id) == normalized_food_id:
                    return item
                if normalized_food_name:
                    food = db.get(Food, str(item.food_id))
                    food_name_candidates = [
                        getattr(food, "dish_name_vi", None) if food else None,
                        getattr(food, "name", None) if food else None,
                        getattr(food, "name_vi", None) if food else None,
                        getattr(food, "display_name", None) if food else None,
                        getattr(food, "original_name", None) if food else None,
                        item.reason,
                    ]
                    if any(
                        normalized_food_name == str(candidate).strip().lower()
                        for candidate in food_name_candidates
                        if candidate
                    ):
                        return item

        return None

    resolved_item = resolve_meal_plan_item()
    if resolved_item is not None:
        meal_plan_item_id = resolved_item.id
        food_id_str = str(resolved_item.food_id)
        print("[MEAL CONSUMPTION TOGGLE MATCH]", {
            "meal_plan_item_id": resolved_item.id,
            "food_id": resolved_item.food_id,
        })

    # 1. Update FoodLogItem check-in first (only if we found a specific meal plan item)
    if resolved_item is not None:
        try:
            _require_recommendation_controller().check_in_meal_plan_item(
                db,
                current_user,
                meal_plan_item_id=meal_plan_item_id,
                eaten=payload.is_eaten,
                serving_grams=None,
            )
        except Exception as e:
            logger.exception("[MEAL CONSUMPTION TOGGLE] Exception in check_in_meal_plan_item for meal_plan_item_id=%s: %s", meal_plan_item_id, str(e))
            # Don't fail the whole request, just log the error and continue with MealConsumptionLog
            print("[MEAL CONSUMPTION TOGGLE] Failed to update meal plan item, continuing with consumption log")

    # 2. Update MealConsumptionLog for Stats Page
    log_food_ids = [value for value in {food_id_str, original_food_id_str} if value is not None]
    log = db.query(MealConsumptionLog).filter(
        MealConsumptionLog.user_id == current_user.id,
        MealConsumptionLog.meal_plan_id == payload.meal_plan_id,
        MealConsumptionLog.food_id.in_(log_food_ids),
        MealConsumptionLog.meal_type == meal_type,
        func.date(MealConsumptionLog.consumed_at) == today
    ).first() if log_food_ids else None

    if not payload.is_eaten:
        logs_to_delete = db.query(MealConsumptionLog).filter(
            MealConsumptionLog.user_id == current_user.id,
            MealConsumptionLog.meal_plan_id == payload.meal_plan_id,
            MealConsumptionLog.food_id.in_(log_food_ids),
            MealConsumptionLog.meal_type == meal_type,
            func.date(MealConsumptionLog.consumed_at) == today
        ).all() if log_food_ids else []
        for existing_log in logs_to_delete:
            db.delete(existing_log)
        if logs_to_delete:
            db.commit()
        print("[MEAL ITEM CONSUMPTION SAVED]", {
            "user_id": current_user.id,
            "meal_plan_id": payload.meal_plan_id,
            "meal_type": meal_type,
            "food_id": food_id_str,
            "item_id": meal_plan_item_id,
            "is_eaten": False,
            "log_date": today.isoformat(),
        })
        print("[MEAL CONSUMPTION TOGGLE RESULT] success: True, is_eaten: False")
        return {
            "success": True,
            "is_eaten": False,
            "meal_plan_id": payload.meal_plan_id,
            "meal_type": meal_type,
            "food_id": food_id_str,
            "meal_plan_item_id": meal_plan_item_id,
        }
    else:
        if not log:
            # Get kcal and protein
            kcal, protein = 0.0, 0.0
            
            # Extract macros directly from MealPlanItem if possible
            if meal_plan_item_id is not None:
                item = db.get(MealPlanItem, meal_plan_item_id)
                if item:
                    kcal = item.kcal or 0.0
                    protein = item.protein or 0.0
            print("[MEAL ITEM CONSUMPTION SAVED]", {
                "user_id": current_user.id,
                "meal_plan_id": payload.meal_plan_id,
                "meal_type": meal_type,
                "food_id": food_id_str,
                "item_id": meal_plan_item_id,
                "is_eaten": True,
                "log_date": today.isoformat(),
            })

            log = MealConsumptionLog(
                user_id=current_user.id,
                meal_plan_id=payload.meal_plan_id,
                food_id=food_id_str,
                meal_type=meal_type,
                kcal=kcal,
                protein=protein,
                status="eaten",
                consumed_at=datetime.now(app_tz).replace(tzinfo=None),
            )
            db.add(log)
            db.commit()
        else:
            log.food_id = food_id_str
            log.status = "eaten"
            log.consumed_at = datetime.now(app_tz).replace(tzinfo=None)
            db.commit()

        print("[MEAL CONSUMPTION TOGGLE SAVED] Created/Updated MealConsumptionLog", {
            "saved": True,
            "record_id": log.id if log else None,
            "meal_plan_id": payload.meal_plan_id,
            "meal_type": meal_type,
            "food_id": food_id_str,
            "is_eaten": True
        })
        print("[MEAL CONSUMPTION TOGGLE RESULT] success: True, is_eaten: True")
        return {
            "success": True,
            "is_eaten": True,
            "meal_plan_id": payload.meal_plan_id,
            "meal_type": meal_type,
            "food_id": food_id_str,
            "meal_plan_item_id": meal_plan_item_id,
        }

@router.get("/meal-consumption/stats", tags=["meal-consumption"])
def get_meal_consumption_stats(
    period: str = Query("day", regex="^(day|month|year)$"),
    date_str: str | None = Query(None, alias="date"),
    month_str: str | None = Query(None, alias="month"),
    year_str: str | None = Query(None, alias="year"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    query = db.query(MealConsumptionLog).filter(MealConsumptionLog.user_id == current_user.id)
    
    if period == "day":
        target_date = date.today()
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                pass
        query = query.filter(func.date(MealConsumptionLog.consumed_at) == target_date)
        
        logs = query.all()
        total_kcal = sum(log.kcal for log in logs)
        total_protein = sum(log.protein for log in logs)
        
        groups_dict = {}
        for log in logs:
            if log.meal_type not in groups_dict:
                groups_dict[log.meal_type] = []
            
            food_name = log.food_id
            food = db.query(Food).filter(Food.food_id == str(log.food_id)).first()
            if food:
                food_name = food.name
                
            groups_dict[log.meal_type].append({
                "food_id": log.food_id,
                "food_name": food_name,
                "kcal": log.kcal,
                "protein": log.protein,
                "consumed_at": log.consumed_at.isoformat()
            })
            
        groups = [{"meal_type": mt, "items": items} for mt, items in groups_dict.items()]
        
        return {
            "period": "day",
            "date": target_date.isoformat(),
            "total_kcal": total_kcal,
            "total_protein": total_protein,
            "total_items": len(logs),
            "groups": groups
        }
    
    elif period == "month":
        target_month = date.today().strftime("%Y-%m")
        if month_str:
            target_month = month_str
            
        try:
            month_year, month_num = target_month.split("-")
            target_year_int = int(month_year)
            target_month_int = int(month_num)
        except ValueError:
            target_year_int = date.today().year
            target_month_int = date.today().month

        logs = query.filter(func.extract("year", MealConsumptionLog.consumed_at) == target_year_int).filter(func.extract("month", MealConsumptionLog.consumed_at) == target_month_int).all()
        total_kcal = sum(log.kcal for log in logs)
        total_protein = sum(log.protein for log in logs)
        
        daily_dict = {}
        for log in logs:
            day_str = log.consumed_at.date().isoformat()
            if day_str not in daily_dict:
                daily_dict[day_str] = {"date": day_str, "total_kcal": 0, "total_protein": 0, "total_items": 0}
            daily_dict[day_str]["total_kcal"] += log.kcal
            daily_dict[day_str]["total_protein"] += log.protein
            daily_dict[day_str]["total_items"] += 1
            
        return {
            "period": "month",
            "month": target_month,
            "total_kcal": total_kcal,
            "total_protein": total_protein,
            "total_items": len(logs),
            "active_days": len(daily_dict),
            "daily_summary": sorted(daily_dict.values(), key=lambda x: x["date"])
        }
        
    elif period == "year":
        target_year = str(date.today().year)
        if year_str:
            target_year = year_str
            
        try:
            target_year_int = int(target_year)
        except ValueError:
            target_year_int = date.today().year

        logs = query.filter(func.extract("year", MealConsumptionLog.consumed_at) == target_year_int).all()
        total_kcal = sum(log.kcal for log in logs)
        total_protein = sum(log.protein for log in logs)
        
        monthly_dict = {}
        for log in logs:
            month_str = log.consumed_at.strftime("%Y-%m")
            if month_str not in monthly_dict:
                monthly_dict[month_str] = {"month": month_str, "total_kcal": 0, "total_protein": 0, "total_items": 0}
            monthly_dict[month_str]["total_kcal"] += log.kcal
            monthly_dict[month_str]["total_protein"] += log.protein
            monthly_dict[month_str]["total_items"] += 1
            
        return {
            "period": "year",
            "year": target_year,
            "total_kcal": total_kcal,
            "total_protein": total_protein,
            "total_items": len(logs),
            "monthly_summary": sorted(monthly_dict.values(), key=lambda x: x["month"])
        }


@router.get("/nutrition-statistics", response_model=NutritionStatisticsResponse, tags=["nutrition-statistics"])
def get_nutrition_statistics(
    range: str = Query("today", pattern="^(today|month|year)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NutritionStatisticsResponse:
    try:
        return NutritionStatisticsResponse(**nutrition_statistics_service.get_statistics(db, current_user, range))
    except Exception as exc:
        import logging
        from fastapi import HTTPException

        logging.getLogger(__name__).exception("[NUTRITION STATISTICS ERROR]")
        raise HTTPException(status_code=500, detail="Cannot load nutrition statistics") from exc


@router.get("/meal-consumption/statistics", response_model=NutritionStatisticsResponse, tags=["nutrition-statistics"])
def get_nutrition_statistics_alias(
    range: str = Query("today", pattern="^(today|month|year)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NutritionStatisticsResponse:
    return get_nutrition_statistics(range=range, db=db, current_user=current_user)


@router.get("/nutrition/eating-history", tags=["nutrition-statistics"])
def get_eating_history(
    mode: str = Query("day", pattern="^(day|month|year)$"),
    date_str: str | None = Query(None, alias="date"),
    month: str | None = Query(None),
    year: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    try:
        return nutrition_statistics_service.get_eating_history(
            db,
            current_user,
            mode=mode,
            date_value=date_str,
            month_value=month,
            year_value=year,
        )
    except Exception as exc:
        import logging

        logging.getLogger(__name__).exception("[EATING HISTORY ERROR]")
        raise HTTPException(status_code=500, detail="Cannot load eating history") from exc



@router.get("/meal-plans/today", response_model=TodayMealPlanResponse, tags=["meal-plans"])
def get_today_meal_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TodayMealPlanResponse:
    return TodayMealPlanResponse(**_require_recommendation_controller().today_meal_plan(db, current_user))



@router.get("/gamification/summary", response_model=dict, tags=["gamification"])
def gamification_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return gamification_service.get_summary(db, current_user)


@router.post("/gamification/challenges/complete", tags=["gamification"])
def complete_gamification_challenge(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    key = payload.get("challenge_key") if isinstance(payload, dict) else None
    if not key:
        return {"success": False, "message": "Missing challenge_key"}
    return gamification_service.complete_challenge(db, current_user, key)


@router.post("/gamification/recalculate", tags=["gamification"])
def gamification_recalculate(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict:
    gamification_service.recalculate(db)
    return {"status": "ok"}


@router.post(
    "/meal-plan-items/{meal_plan_item_id}/check-in",
    response_model=TodayMealPlanResponse,
    tags=["meal-plans"],
)
def check_in_meal_plan_item(
    meal_plan_item_id: int,
    payload: MealPlanItemCheckInInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TodayMealPlanResponse:
    return TodayMealPlanResponse(
        **_require_recommendation_controller().check_in_meal_plan_item(
            db,
            current_user,
            meal_plan_item_id=meal_plan_item_id,
            eaten=payload.eaten,
            serving_grams=payload.serving_grams,
        )
    )


@router.get(
    "/recommendations/history",
    response_model=RecommendationHistoryResponse,
    tags=["recommendations"],
)
def list_history(
    limit: int = Query(10, ge=1, le=100),
    period: str = Query("all", pattern="^(all|day|week)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendationHistoryResponse:
    return _require_recommendation_controller().list_history(db=db, user=current_user, limit=limit, period=period)


@router.get(
    "/recommendations/history/{request_id}",
    response_model=RecommendationHistoryDetail,
    tags=["recommendations"],
)
def history_detail(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendationHistoryDetail:
    return _require_recommendation_controller().history_detail(db=db, user=current_user, request_id=request_id)


@router.post("/admin/foods", response_model=FoodView, tags=["admin"])
def admin_create_food(
    payload: FoodCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> FoodView:
    return FoodView(**food_service.create_food(db, payload))


@router.put("/admin/foods/{food_id}", response_model=FoodView, tags=["admin"])
def admin_update_food(
    food_id: str,
    payload: FoodUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> FoodView:
    return FoodView(**food_service.update_food(db, food_id, payload))


@router.delete("/admin/foods/{food_id}", tags=["admin"])
def admin_delete_food(
    food_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, bool]:
    return food_service.delete_food(db, food_id)


@router.get("/admin/categories", response_model=FoodCategoryListResponse, tags=["admin"])
def admin_list_categories(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> FoodCategoryListResponse:
    return FoodCategoryListResponse(**food_service.list_categories(db))


@router.post("/admin/categories", response_model=FoodCategoryView, tags=["admin"])
def admin_create_category(
    payload: FoodCategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> FoodCategoryView:
    return FoodCategoryView(**food_service.create_category(db, payload))


@router.put("/admin/categories/{category_id}", response_model=FoodCategoryView, tags=["admin"])
def admin_update_category(
    category_id: int,
    payload: FoodCategoryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> FoodCategoryView:
    return FoodCategoryView(**food_service.update_category(db, category_id, payload))


@router.delete("/admin/categories/{category_id}", tags=["admin"])
def admin_delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict[str, bool]:
    return food_service.delete_category(db, category_id)


@router.get("/admin/users/stats", response_model=AdminStatsResponse, tags=["admin"])
def admin_user_stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AdminStatsResponse:
    return AdminStatsResponse(**user_service.admin_stats(db))


@router.get("/admin/users", response_model=AdminUserListResponse, tags=["admin"])
def admin_list_users(
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    bmi_category: str | None = Query(default=None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AdminUserListResponse:
    return AdminUserListResponse(**_require_admin_service().list_users(db, q, status, bmi_category, limit, offset))


@router.get("/admin/overview", response_model=AdminOverviewResponse, tags=["admin"])
def admin_overview(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AdminOverviewResponse:
    return AdminOverviewResponse(**_require_admin_service().overview(db))


@router.get("/admin/users/{user_id}", tags=["admin"])
def admin_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    return _require_admin_service().user_detail(db, user_id)


@router.patch("/admin/users/{user_id}/status", response_model=UserView, tags=["admin"])
def admin_update_user_status(
    user_id: int,
    payload: AccountStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserView:
    values = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else payload.dict(exclude_unset=True)
    return UserView(**_require_admin_service().update_user_status(db, user_id, values))


@router.get("/admin/foods", response_model=AdminFoodListResponse, tags=["admin"])
def admin_list_foods(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    menu_eligible: bool | None = Query(default=None),
    missing_image: bool = Query(False),
    has_quality_flags: bool = Query(False),
    image_status: str | None = Query(default=None, pattern="^(pexels_pending|verified_real)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AdminFoodListResponse:
    return AdminFoodListResponse(
        **_require_admin_service().list_foods(db, q, category, menu_eligible, missing_image, has_quality_flags, image_status, limit, offset)
    )


@router.get("/admin/foods/{food_id}", tags=["admin"])
def admin_get_food(
    food_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    return _require_admin_service().get_food(db, food_id)


@router.patch("/admin/foods/{food_id}", tags=["admin"])
def admin_patch_food(
    food_id: str,
    payload: FoodUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    return _require_admin_service().update_food(db, food_id, payload)


@router.post("/admin/foods/{food_id}/exclude-from-recommendations", tags=["admin"])
def admin_exclude_food_from_recommendations(
    food_id: str,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    reason = payload.get("reason") if isinstance(payload, dict) else None
    return _require_admin_service().exclude_food_from_recommendations(db, food_id, reason)


@router.post("/admin/foods/{food_id}/restore-to-recommendations", tags=["admin"])
def admin_restore_food_to_recommendations(
    food_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    return _require_admin_service().restore_food_to_recommendations(db, food_id)


@router.post("/admin/food-images/{food_id}/refetch", tags=["admin"])
def admin_refetch_food_image(
    food_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    return _require_admin_service().refetch_food_image(db, food_id)


@router.get("/admin/food-categories/summary", response_model=AdminCategorySummaryResponse, tags=["admin"])
def admin_food_category_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AdminCategorySummaryResponse:
    return AdminCategorySummaryResponse(**_require_admin_service().category_summary(db))


@router.post("/admin/recommendation-test", response_model=RecommendationOutput, tags=["admin"])
def admin_recommendation_test(
    payload: RecommendationInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> RecommendationOutput:
    return RecommendationOutput(**_require_admin_service().recommendation_test(db, current_user, payload))


@router.get("/admin/meal-plans", response_model=AdminMealPlanListResponse, tags=["admin"])
def admin_list_meal_plans(
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    only_errors: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AdminMealPlanListResponse:
    return AdminMealPlanListResponse(**_require_admin_service().list_meal_plans(db, q, status, only_errors, limit, offset))


@router.get("/admin/meal-plans/{meal_plan_id}", tags=["admin"])
def admin_meal_plan_detail(
    meal_plan_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    return _require_admin_service().meal_plan_detail(db, meal_plan_id)


@router.get("/admin/system-errors", response_model=AdminSystemErrorListResponse, tags=["admin"])
def admin_list_system_errors(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AdminSystemErrorListResponse:
    return AdminSystemErrorListResponse(**_require_admin_service().list_system_errors(db, limit, offset))


@router.patch("/admin/system-errors/{error_id}/resolve", tags=["admin"])
def admin_resolve_system_error(
    error_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    return _require_admin_service().resolve_error(db, error_id)
