from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.controllers.recommendation_controller import controller
from app.core.database import get_db
from app.models.entities import User
from app.services.auth_service import AuthService
from app.services.food_service import FoodService, InteractionService, UserService
from app.views.schemas import (
    AccountStatusUpdate,
    AdminStatsResponse,
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
    MealPlanItemCheckInInput,
    MealPlanRegenerateInput,
    RecommendationHistoryDetail,
    RecommendationHistoryResponse,
    RecommendationInput,
    RecommendationOutput,
    TodayMealPlanResponse,
    UserCreate,
    UserLogin,
    UserProfileInput,
    UserProfileView,
    UserUpdate,
    UserView,
)


router = APIRouter(prefix="/api/v1")
auth_service = AuthService()
food_service = FoodService()
user_service = UserService()
interaction_service = InteractionService()


@router.get("/health", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/auth/register", response_model=AuthTokenResponse, tags=["auth"])
def register(payload: UserCreate, db: Session = Depends(get_db)) -> AuthTokenResponse:
    return auth_service.register(payload, db)


@router.post("/auth/login", response_model=AuthTokenResponse, tags=["auth"])
def login(payload: UserLogin, db: Session = Depends(get_db)) -> AuthTokenResponse:
    return auth_service.login(payload, db)


@router.get("/users/me", response_model=CurrentUserView, tags=["users"])
def get_me(current_user: User = Depends(get_current_user)) -> CurrentUserView:
    return CurrentUserView(**user_service.get_me(current_user))


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
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AdminUserListResponse:
    return AdminUserListResponse(**user_service.list_users(db, limit, offset))


@router.patch("/admin/users/{user_id}/status", response_model=UserView, tags=["admin"])
def admin_update_user_status(
    user_id: int,
    payload: AccountStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserView:
    return UserView(**user_service.update_account_status(db, user_id, payload))
