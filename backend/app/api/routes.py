from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.controllers.recommendation_controller import controller
from app.core.database import get_db
from app.models.entities import User
from app.services.auth_service import AuthService
from app.services.admin_service import AdminService
from app.services.food_service import FoodService, InteractionService, UserService
from app.services.weight_log_service import WeightLogService
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
    MessageResponse,
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
    WeightMilestoneResponse,
    WeightLogResponse,
    WeightLogSummary,
)


router = APIRouter(prefix="/api/v1")
auth_service = AuthService()
food_service = FoodService()
user_service = UserService()
interaction_service = InteractionService()
weight_log_service = WeightLogService()
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


@router.post("/weight-logs", response_model=WeightLogResponse, tags=["weight-logs"])
def upsert_weight_log(
    payload: WeightLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WeightLogResponse:
    return WeightLogResponse(**weight_log_service.save_log(db, current_user, payload))


@router.get("/weight-logs", response_model=list[WeightMilestoneResponse], tags=["weight-logs"])
def list_weight_logs(
    range: str = Query("30", pattern="^(30|90|all)$"),
    mode: str = Query("milestones", pattern="^(milestones|all)$"),
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


@router.get("/meal-plans/today", response_model=TodayMealPlanResponse, tags=["meal-plans"])
def get_today_meal_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TodayMealPlanResponse:
    return TodayMealPlanResponse(**controller.today_meal_plan(db, current_user))


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
