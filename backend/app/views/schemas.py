from __future__ import annotations

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    full_name: str | None = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserUpdate(BaseModel):
    email: str | None = None
    full_name: str | None = None
    current_password: str | None = None
    password: str | None = Field(default=None, min_length=8)


class UserProfileInput(BaseModel):
    weight_kg: float | None = Field(default=None, gt=0)
    height_cm: float | None = Field(default=None, gt=0)
    age: int | None = Field(default=None, ge=1, le=120)
    sex: str | None = None
    activity_level: str = "moderate"
    surplus_kcal: float | None = Field(default=None, ge=0)
    disliked_foods: list[str] = Field(default_factory=list)
    disliked_food_groups: list[str] = Field(default_factory=list)


class UserProfileView(BaseModel):
    weight_kg: float | None = None
    height_cm: float | None = None
    age: int | None = None
    sex: str | None = None
    activity_level: str = "moderate"
    surplus_kcal: float | None = None
    disliked_foods: list[str] = Field(default_factory=list)
    disliked_food_groups: list[str] = Field(default_factory=list)
    updated_at: str | None = None


class UserView(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    role: str
    is_active: bool
    created_at: str


class CurrentUserView(UserView):
    profile: UserProfileView | None = None


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserView


class AccountStatusUpdate(BaseModel):
    is_active: bool | None = None
    role: str | None = None


class AdminUserListResponse(BaseModel):
    items: list[UserView]
    total: int
    limit: int
    offset: int


class AdminStatsResponse(BaseModel):
    total_users: int
    active_users: int
    admin_users: int


class FoodCreate(BaseModel):
    food_id: str
    name: str
    calories: float = Field(..., ge=0)
    protein: float = Field(..., ge=0)
    fat: float = Field(..., ge=0)
    carbs: float = Field(..., ge=0)
    category: str
    name_vi: str | None = None
    type: str | None = None
    image_url: str | None = None
    source: str | None = None


class FoodUpdate(BaseModel):
    name: str | None = None
    calories: float | None = Field(default=None, ge=0)
    protein: float | None = Field(default=None, ge=0)
    fat: float | None = Field(default=None, ge=0)
    carbs: float | None = Field(default=None, ge=0)
    category: str | None = None
    name_vi: str | None = None
    type: str | None = None
    image_url: str | None = None
    source: str | None = None


class FoodView(BaseModel):
    food_id: str
    name: str
    name_en: str | None = None
    image_url: str | None = None
    category: str
    type: str | None = None
    source: str | None = None
    calories: float
    protein: float
    fat: float
    carbs: float


class FoodListResponse(BaseModel):
    items: list[FoodView]
    total: int
    limit: int
    offset: int


class FoodCategoryCreate(BaseModel):
    name: str
    display_name: str | None = None
    description: str | None = None
    source: str | None = None


class FoodCategoryUpdate(BaseModel):
    name: str | None = None
    display_name: str | None = None
    description: str | None = None
    source: str | None = None


class FoodCategoryView(BaseModel):
    id: int
    name: str
    display_name: str | None = None
    description: str | None = None
    source: str | None = None


class FoodCategoryListResponse(BaseModel):
    items: list[FoodCategoryView]


class FavoriteFoodResponse(BaseModel):
    food_id: str
    is_favorite: bool
    removed: bool | None = None


class FavoriteFoodListResponse(BaseModel):
    items: list[FoodView]


class FoodRatingInput(BaseModel):
    rating: int = Field(..., ge=1, le=5)


class FoodRatingView(BaseModel):
    food_id: str
    rating: int
    updated_at: str


class RecommendationInput(BaseModel):
    weight: float = Field(..., ge=20, le=250)
    height: float = Field(..., ge=100, le=230)
    activity: str = "moderate"
    age: int | None = Field(default=None, ge=1, le=120)
    sex: str | None = None
    goal_type: str = "gain"
    weight_gain_speed: str | None = None
    gain_speed: str | None = None
    meal_complexity: str = "balanced"
    diet_style: str = "balanced"
    diet_type: str | None = None
    budget_level: str = "standard"
    surplus_kcal: float | None = None
    target_calories: float | None = Field(default=None, gt=0)
    target_weight: float | None = Field(default=None, ge=20, le=250)
    min_calories: float | None = Field(default=None, gt=0)
    max_calories: float | None = Field(default=None, gt=0)
    protein_target: float | None = Field(default=None, ge=0)
    fat_target: float | None = Field(default=None, ge=0)
    carb_target: float | None = Field(default=None, ge=0)
    top_n: int = Field(default=10, ge=1, le=50)
    preferred_categories: list[str] = Field(default_factory=list)
    excluded_categories: list[str] = Field(default_factory=list)
    allergens: list[str] = Field(default_factory=list)
    favorites: list[str] = Field(default_factory=list)
    disliked_foods: list[str] = Field(default_factory=list)
    disliked_food_groups: list[str] = Field(default_factory=list)
    energy_tolerance_kcal: float | None = Field(default=80.0, ge=0)
    use_personalization: bool = False
    min_protein_ratio: float = Field(default=0.90, ge=0.0, le=1.0)
    min_fat_ratio: float = Field(default=0.90, ge=0.0, le=1.0)
    macro_backtracking_attempts: int = Field(default=30, ge=0, le=200)
    save_user_data: bool = False


class NutritionTargetView(BaseModel):
    bmi: float
    bmr: float
    tdee: float
    maintenance_kcal: float
    calories: float
    protein: float
    fat: float
    carbs: float
    bmi_status: str | None = None
    medical_warning: str | None = None


class FoodItemView(BaseModel):
    food_id: str
    original_name: str | None = None
    name: str
    image_url: str | None = None
    image_alt: str | None = None
    image_source_type: str | None = None
    image_verified: bool = False
    image_badge: str | None = None
    image_query: str | None = None
    image_requirement: str | None = None
    category: str
    normalized_category: str | None = None
    food_group: str | None = None
    meal_role: str | None = None
    culinary_role: str | None = None
    quantity_g: float | None = None
    serving_grams: float | None = None
    serving_display: str | None = None
    portion_display: str | None = None
    serving_multiplier: float | None = None
    kcal: float | None = None
    calories: float
    protein: float
    fat: float
    carbs: float
    reason: str | None = None
    status: str | None = "suggested"
    quality_flags: str | None = None
    score: float


class EvaluationView(BaseModel):
    target_calories: float
    recommended_calories: float
    signed_error: float
    absolute_error: float
    relative_error_pct: float
    within_10pct: bool
    macro_mae_relative_pct: float
    macros_within_20pct_ratio: float
    preference_precision_pct: float | None = None
    meal_calorie_ratio_targets: dict[str, float] = Field(default_factory=dict)
    meal_macro_distribution: dict[str, dict[str, float]] = Field(default_factory=dict)
    validation: dict = Field(default_factory=dict)


class MealPlanItemCheckInInput(BaseModel):
    eaten: bool = True
    serving_grams: float | None = Field(default=None, gt=0)


class TodayMealPlanResponse(BaseModel):
    has_plan: bool
    generate_required: bool
    message: str = ""
    meal_plan: dict | None = None
    meals: list[dict] = Field(default_factory=list)
    food_log: dict | None = None


class EligibilityCheckView(BaseModel):
    bmi: float | None = None
    weight_status: str
    eligible: bool
    reason: str


class OverallAssessmentView(BaseModel):
    score: float
    summary: str
    main_problems: list[str] = Field(default_factory=list)


class DetectedIssueView(BaseModel):
    meal: str
    item_name: str
    issue_type: str
    severity: str
    evidence: str
    reason: str
    suggested_fix: str


class FixedMenuItemView(BaseModel):
    old_item: str | None = None
    new_item: str
    category: str
    portion_display: str
    kcal: float
    protein: float
    fat: float
    carb: float
    image_requirement: str
    reason: str


class FixedMenuMealView(BaseModel):
    meal: str
    items: list[FixedMenuItemView] = Field(default_factory=list)


class RecommendationOutput(BaseModel):
    eligibility_check: EligibilityCheckView
    overall_assessment: OverallAssessmentView
    detected_issues: list[DetectedIssueView] = Field(default_factory=list)
    fixed_menu: list[FixedMenuMealView] = Field(default_factory=list)
    validation_rules_to_add: list[str] = Field(default_factory=list)
    target: NutritionTargetView
    top_recommendations: list[FoodItemView]
    meal_plan: dict[str, list[FoodItemView]]
    evaluation: EvaluationView


class RecommendationHistoryItem(BaseModel):
    id: int
    created_at: str
    target_calories: float
    bmr: float | None = None
    tdee: float | None = None
    recommended_calories: float
    relative_error_pct: float
    precision_pct: float | None


class RecommendationHistoryResponse(BaseModel):
    items: list[RecommendationHistoryItem]


class RecommendationHistoryDetail(RecommendationHistoryItem):
    meal_plan: dict[str, list[FoodItemView]]
