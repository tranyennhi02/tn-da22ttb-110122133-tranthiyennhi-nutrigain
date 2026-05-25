from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.api.v1.routes.ai_chat import router as ai_chat_router
from app.controllers.recommendation_controller import controller
from app.core.database import get_db
from app.models.entities import User
from app.services.auth_service import AuthService
from app.services.admin_service import AdminService
from app.services.food_service import FoodService, InteractionService, UserService
from app.services.nutrition_statistics_service import NutritionStatisticsService
from app.services.ingredient_recognition_service import recognize_ingredients_from_image
from app.services.clip_ingredient_service import recognize_ingredients_with_clip
from app.services.weight_log_service import WeightLogService
from app.services.gamification_service import GamificationService
from app.services.meal_reminder_service import send_test_meal_reminder_email
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
    MealReminderTestEmailInput,
    MealReminderTestEmailResponse,
    MealConsumptionToggleInput,
    MessageResponse,
    NutritionStatisticsResponse,
    RecommendationHistoryDetail,
    RecommendationHistoryResponse,
    RecommendationInput,
    RecommendationOutput,
    ResetPasswordInput,
    TodayMealPlanResponse,
    UserCreate,
    UserLogin,
    GoogleLoginInput,
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
router.include_router(ai_chat_router)
auth_service = AuthService()
food_service = FoodService()
user_service = UserService()
interaction_service = InteractionService()
weight_log_service = WeightLogService()
nutrition_statistics_service = NutritionStatisticsService()
gamification_service = GamificationService()
admin_service = AdminService()


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


@router.post("/auth/register", response_model=AuthTokenResponse, tags=["auth"])
def register(payload: UserCreate, db: Session = Depends(get_db)) -> AuthTokenResponse:
    return auth_service.register(payload, db)


@router.post("/auth/login", response_model=AuthTokenResponse, tags=["auth"])
def login(payload: UserLogin, db: Session = Depends(get_db)) -> AuthTokenResponse:
    return auth_service.login(payload, db)


@router.post("/auth/google", response_model=AuthTokenResponse, tags=["auth"])
def google_login(payload: GoogleLoginInput, db: Session = Depends(get_db)) -> AuthTokenResponse:
    return auth_service.google_login(payload.id_token, db)


@router.post("/auth/forgot-password", response_model=MessageResponse, tags=["auth"])
def forgot_password(payload: ForgotPasswordInput, db: Session = Depends(get_db)) -> MessageResponse:
    return MessageResponse(**auth_service.forgot_password(payload, db))


@router.post("/auth/reset-password", response_model=MessageResponse, tags=["auth"])
def reset_password(payload: ResetPasswordInput, db: Session = Depends(get_db)) -> MessageResponse:
    return MessageResponse(**auth_service.reset_password(payload, db))


@router.get("/users/me", response_model=CurrentUserView, tags=["users"])
def get_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CurrentUserView:
    return CurrentUserView(**user_service.get_me(db, current_user))


@router.put("/users/me", response_model=CurrentUserView, tags=["users"])
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CurrentUserView:
    return CurrentUserView(**user_service.update_me(db, current_user, payload))


@router.put("/users/me/profile", response_model=UserProfileView, tags=["users"])
def update_profile(
    payload: UserProfileInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileView:
    return UserProfileView(**user_service.update_profile(db, current_user, payload))


@router.post("/meal-reminders/test-email", response_model=MealReminderTestEmailResponse, tags=["meal-reminders"])
def test_meal_reminder_email(
    payload: MealReminderTestEmailInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MealReminderTestEmailResponse:
    success, message, sent_to = send_test_meal_reminder_email(current_user, payload.meal_type)
    return MealReminderTestEmailResponse(success=success, message=message, sent_to=sent_to)


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
    return controller.create_recommendation(payload, db, current_user)


@router.post("/meal-plans/regenerate", response_model=RecommendationOutput, tags=["meal-plans"])
def regenerate_meal_plan(
    payload: MealPlanRegenerateInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecommendationOutput:
    return controller.regenerate_meal_plan(payload, db, current_user)


@router.post("/meal-plans/recognize-ingredients", tags=["meal-plans"])
async def recognize_ingredients(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return await recognize_ingredients_from_image(file)


@router.post("/ingredients/recognize-image", tags=["ingredients"])
async def recognize_ingredient_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    content_type = (file.content_type or "").lower()
    print("[INGREDIENT RECOGNITION RECEIVED]", {
        "filename": file.filename,
        "content_type": content_type,
    })
    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        response = {
            "success": False,
            "ingredients": [],
            "raw_labels": [],
            "confidence": 0,
            "method": "clip",
            "message": "Vui l\u00f2ng ch\u1ecdn \u1ea3nh JPG, PNG ho\u1eb7c WEBP.",
        }
        print("[INGREDIENT RECOGNITION RESULT]", response)
        return response

    image_bytes = await file.read()
    if not image_bytes:
        response = {
            "success": False,
            "ingredients": [],
            "raw_labels": [],
            "confidence": 0,
            "method": "clip",
            "message": "Kh\u00f4ng nh\u1eadn di\u1ec7n \u0111\u01b0\u1ee3c nguy\u00ean li\u1ec7u r\u00f5 r\u00e0ng. B\u1ea1n c\u00f3 th\u1ec3 nh\u1eadp th\u1ee7 c\u00f4ng.",
        }
        print("[INGREDIENT RECOGNITION RESULT]", response)
        return response

    try:
        return recognize_ingredients_with_clip(image_bytes, filename=file.filename)
    except Exception as exc:
        print("[INGREDIENT RECOGNITION ERROR]", str(exc))
        response = {
            "success": False,
            "ingredients": [],
            "raw_labels": [],
            "confidence": 0,
            "method": "clip",
            "message": "Kh\u00f4ng nh\u1eadn di\u1ec7n \u0111\u01b0\u1ee3c nguy\u00ean li\u1ec7u r\u00f5 r\u00e0ng. B\u1ea1n c\u00f3 th\u1ec3 nh\u1eadp th\u1ee7 c\u00f4ng.",
        }
        print("[INGREDIENT RECOGNITION RESULT]", response)
        return response



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

    print("[MEAL CONSUMPTION TOGGLE PAYLOAD]", {
        "meal_plan_id": payload.meal_plan_id,
        "meal_type": payload.meal_type,
        "meal_plan_item_id": payload.meal_plan_item_id,
        "food_id": payload.food_id,
        "is_eaten": payload.is_eaten
    })

    # Try to resolve meal_plan_item_id if not provided
    resolved_via_db = False
    if payload.meal_plan_item_id is None and payload.meal_plan_id is not None and payload.meal_type is not None and payload.food_id is not None:
        try:
            food_id_str = str(payload.food_id)
            resolved_item = db.execute(
                select(MealPlanItem)
                .join(Meal, MealPlanItem.meal_id == Meal.id)
                .where(Meal.meal_plan_id == int(payload.meal_plan_id))
                .where(func.lower(Meal.meal_type) == func.lower(payload.meal_type))
                .where(MealPlanItem.food_id == food_id_str)
            ).scalars().first()
            
            if resolved_item:
                payload.meal_plan_item_id = resolved_item.id
                resolved_via_db = True
                print("[MEAL CONSUMPTION TOGGLE MATCH] Resolved meal_plan_item_id:", resolved_item.id)
        except Exception as e:
            logger.exception("Failed to resolve meal_plan_item_id from db: %s", e)

    # 1. Update FoodLogItem check-in first
    if payload.meal_plan_item_id is not None:
        try:
            controller.check_in_meal_plan_item(
                db,
                current_user,
                meal_plan_item_id=payload.meal_plan_item_id,
                eaten=payload.is_eaten,
                serving_grams=None,
            )
            print("[MEAL CONSUMPTION TOGGLE SAVED] check_in_meal_plan_item done for:", payload.meal_plan_item_id)
        except Exception as e:
            logger.warning("[MEAL CONSUMPTION TOGGLE] Exception in check_in_meal_plan_item for meal_plan_item_id=%s: %s", payload.meal_plan_item_id, str(e))

    # 2. Update MealConsumptionLog for Stats Page
    today = date.today()
    log = db.query(MealConsumptionLog).filter(
        MealConsumptionLog.user_id == current_user.id,
        MealConsumptionLog.meal_plan_id == payload.meal_plan_id,
        MealConsumptionLog.food_id == (str(payload.food_id) if payload.food_id is not None else None),
        MealConsumptionLog.meal_type == payload.meal_type,
        func.date(MealConsumptionLog.consumed_at) == today
    ).first()

    if not payload.is_eaten:
        if log:
            db.delete(log)
            db.commit()
        print("[MEAL CONSUMPTION TOGGLE SAVED] Deleted MealConsumptionLog", {
            "meal_plan_id": payload.meal_plan_id,
            "meal_type": payload.meal_type,
            "food_id": payload.food_id,
            "is_eaten": False
        })
        print("[MEAL CONSUMPTION TOGGLE RESULT] success: True, is_eaten: False")
        return {
            "success": True,
            "is_eaten": False,
            "meal_plan_id": payload.meal_plan_id,
            "meal_type": payload.meal_type,
            "food_id": payload.food_id,
            "meal_plan_item_id": payload.meal_plan_item_id
        }
    else:
        if not log:
            # Get kcal and protein
            kcal, protein = 0.0, 0.0
            
            # Extract macros directly from MealPlanItem if possible
            if payload.meal_plan_item_id is not None:
                item = db.get(MealPlanItem, payload.meal_plan_item_id)
                if item:
                    kcal = item.kcal or 0.0
                    protein = item.protein or 0.0
            
            # Lookup from Food database as fallback
            if (kcal == 0.0 and protein == 0.0) and payload.food_id is not None:
                food_id_str = str(payload.food_id)
                food = db.query(Food).filter(Food.food_id == food_id_str).first()
                if food:
                    kcal = (
                        getattr(food, "kcal", None)
                        or getattr(food, "calories", None)
                        or getattr(food, "energy_kcal", None)
                        or 0.0
                    )
                    protein = (
                        getattr(food, "protein", None)
                        or getattr(food, "protein_g", None)
                        or 0.0
                    )

            log = MealConsumptionLog(
                user_id=current_user.id,
                meal_plan_id=payload.meal_plan_id,
                food_id=(str(payload.food_id) if payload.food_id is not None else None),
                meal_type=payload.meal_type,
                kcal=kcal,
                protein=protein,
                status="eaten"
            )
            db.add(log)
            db.commit()
        else:
            log.status = "eaten"
            db.commit()

        print("[MEAL CONSUMPTION TOGGLE SAVED] Created/Updated MealConsumptionLog", {
            "meal_plan_id": payload.meal_plan_id,
            "meal_type": payload.meal_type,
            "food_id": payload.food_id,
            "is_eaten": True
        })
        print("[MEAL CONSUMPTION TOGGLE RESULT] success: True, is_eaten: True")
        return {
            "success": True,
            "is_eaten": True,
            "meal_plan_id": payload.meal_plan_id,
            "meal_type": payload.meal_type,
            "food_id": payload.food_id,
            "meal_plan_item_id": payload.meal_plan_item_id
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



@router.get("/meal-plans/today", response_model=TodayMealPlanResponse, tags=["meal-plans"])
def get_today_meal_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TodayMealPlanResponse:
    return TodayMealPlanResponse(**controller.today_meal_plan(db, current_user))



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
        **controller.check_in_meal_plan_item(
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
    return controller.list_history(db=db, user=current_user, limit=limit, period=period)


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
    return controller.history_detail(db=db, user=current_user, request_id=request_id)


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
    return AdminUserListResponse(**admin_service.list_users(db, q, status, bmi_category, limit, offset))


@router.get("/admin/overview", response_model=AdminOverviewResponse, tags=["admin"])
def admin_overview(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AdminOverviewResponse:
    return AdminOverviewResponse(**admin_service.overview(db))


@router.get("/admin/users/{user_id}", tags=["admin"])
def admin_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    return admin_service.user_detail(db, user_id)


@router.patch("/admin/users/{user_id}/status", response_model=UserView, tags=["admin"])
def admin_update_user_status(
    user_id: int,
    payload: AccountStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserView:
    values = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else payload.dict(exclude_unset=True)
    return UserView(**admin_service.update_user_status(db, user_id, values))


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
        **admin_service.list_foods(db, q, category, menu_eligible, missing_image, has_quality_flags, image_status, limit, offset)
    )


@router.get("/admin/foods/{food_id}", tags=["admin"])
def admin_get_food(
    food_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    return admin_service.get_food(db, food_id)


@router.patch("/admin/foods/{food_id}", tags=["admin"])
def admin_patch_food(
    food_id: str,
    payload: FoodUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    return admin_service.update_food(db, food_id, payload)


@router.post("/admin/foods/{food_id}/exclude-from-recommendations", tags=["admin"])
def admin_exclude_food_from_recommendations(
    food_id: str,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    reason = payload.get("reason") if isinstance(payload, dict) else None
    return admin_service.exclude_food_from_recommendations(db, food_id, reason)


@router.post("/admin/foods/{food_id}/restore-to-recommendations", tags=["admin"])
def admin_restore_food_to_recommendations(
    food_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    return admin_service.restore_food_to_recommendations(db, food_id)


@router.post("/admin/food-images/{food_id}/refetch", tags=["admin"])
def admin_refetch_food_image(
    food_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    return admin_service.refetch_food_image(db, food_id)


@router.get("/admin/food-categories/summary", response_model=AdminCategorySummaryResponse, tags=["admin"])
def admin_food_category_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AdminCategorySummaryResponse:
    return AdminCategorySummaryResponse(**admin_service.category_summary(db))


@router.post("/admin/recommendation-test", response_model=RecommendationOutput, tags=["admin"])
def admin_recommendation_test(
    payload: RecommendationInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> RecommendationOutput:
    return RecommendationOutput(**admin_service.recommendation_test(db, current_user, payload))


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
    return AdminMealPlanListResponse(**admin_service.list_meal_plans(db, q, status, only_errors, limit, offset))


@router.get("/admin/meal-plans/{meal_plan_id}", tags=["admin"])
def admin_meal_plan_detail(
    meal_plan_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    return admin_service.meal_plan_detail(db, meal_plan_id)


@router.get("/admin/system-errors", response_model=AdminSystemErrorListResponse, tags=["admin"])
def admin_list_system_errors(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AdminSystemErrorListResponse:
    return AdminSystemErrorListResponse(**admin_service.list_system_errors(db, limit, offset))


@router.patch("/admin/system-errors/{error_id}/resolve", tags=["admin"])
def admin_resolve_system_error(
    error_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    return admin_service.resolve_error(db, error_id)
