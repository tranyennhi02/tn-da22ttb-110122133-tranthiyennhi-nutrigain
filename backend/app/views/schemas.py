from __future__ import annotations

from datetime import date, datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator


class UserCreate(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    full_name: str | None = None


class UserLogin(BaseModel):
    email: str
    password: str


class GoogleLoginInput(BaseModel):
    id_token: str


class ForgotPasswordInput(BaseModel):
    email: str


class ResetPasswordInput(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)


class MessageResponse(BaseModel):
    message: str


class MealReminderTestEmailInput(BaseModel):
    meal_type: str = "test"


class MealReminderTestEmailResponse(BaseModel):
    success: bool
    message: str
    sent_to: str | None = None


class MealConsumptionToggleInput(BaseModel):
    meal_plan_id: int | None = None
    meal_type: str | None = None
    meal_plan_item_id: int | None = None
    food_id: str | None = None
    is_eaten: bool = True


class WeightDailyUpdateInput(BaseModel):
    weight_kg: float = Field(..., gt=0)


class WeightDailyUpdateResponse(BaseModel):
    success: bool
    weight_kg: float | None = None
    log_date: str | None = None
    profile: dict | None = None
    chart_points: list[dict] = Field(default_factory=list)
    summary: dict | None = None


class NutritionStatisticsResponse(BaseModel):
    pass


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
    gender: str | None = None
    activity_level: str = "moderate"
    surplus_kcal: float | None = Field(default=None, ge=0)
    favorite_foods: list[str] = Field(default_factory=list)
    disliked_foods: list[str] = Field(default_factory=list)
    disliked_food_groups: list[str] = Field(default_factory=list)
    target_weight_kg: float | None = Field(default=None, gt=0)
    weight_gain_speed: str | None = None
    diet_type: str | None = None
    diet_style: str | None = None
    budget_level: str | None = None
    items_per_meal: int | None = Field(default=None, ge=1, le=10)

    @field_validator("favorite_foods", mode="before")
    @classmethod
    def normalize_favorite_foods(cls, value: Any):
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

    @field_validator("disliked_foods", "disliked_food_groups", mode="before")
    @classmethod
    def normalize_profile_food_list(cls, value: Any):
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []


class UserProfileView(BaseModel):
    weight_kg: float | None = None
    height_cm: float | None = None
    age: int | None = None
    sex: str | None = None
    gender: str | None = None
    activity_level: str = "moderate"
    surplus_kcal: float | None = None
    favorite_foods: list[str] = Field(default_factory=list)
    disliked_foods: list[str] = Field(default_factory=list)
    disliked_food_groups: list[str] = Field(default_factory=list)
    target_weight_kg: float | None = None
    weight_gain_speed: str | None = None
    diet_type: str | None = None
    budget_level: str | None = None
    items_per_meal: int | None = None
    updated_at: str | None = None


class UserView(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    role: str
    status: str = "ACTIVE"
    is_active: bool
    created_at: str


class CurrentUserView(UserView):
    profile: UserProfileView | None = None


class WeightLogCreate(BaseModel):
    weight_kg: float = Field(..., gt=0)
    log_date: date | None = None
    note: str | None = None
    # source is assigned server-side; frontend should not set it


class WeightLogResponse(BaseModel):
    id: int
    user_id: int
    weight_kg: float
    log_date: date
    note: str | None = None
    source: str | None = None
    is_chart_milestone: bool = False
    created_at: datetime
    updated_at: datetime | None = None


class WeightMilestoneResponse(BaseModel):
    date: str
    log_date: date | None = None
    weight_kg: float
    source: str | None = None
    label: str | None = None
    is_milestone: bool = True
    note: str | None = None


class WeightLogSummary(BaseModel):
    initial_weight: float | None = None
    start_date: date | None = None
    current_weight: float | None = None
    start_weight: float | None = None
    target_weight: float | None = None
    change_kg: float | None = None
    gained_kg: float | None = None
    remaining_kg: float | None = None
    progress_percent: float = 0.0
    trend: str = "not_enough_data"
    last_log_date: date | None = None
    latest_log_date: date | None = None
    latest_log_weight: float | None = None
    all_logs_count: int = 0
    latest_milestone_date: date | None = None
    next_checkin_date: date | None = None
    next_milestone_date: date | None = None
    milestone_points: list[dict] | None = None
    chart_points: list[dict] | None = None
    days_since_latest_milestone: int | None = None
    should_checkin: bool = False
    message: str


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserView


class AccountStatusUpdate(BaseModel):
    is_active: bool | None = None
    status: str | None = None
    role: str | None = None


class AdminUserListResponse(BaseModel):
    items: list[dict]
    total: int
    limit: int
    offset: int


class AdminStatsResponse(BaseModel):
    total_users: int
    active_users: int
    admin_users: int


class AdminOverviewResponse(BaseModel):
    total_users: int
    new_users_today: int
    total_meal_plans: int
    total_foods: int
    eligible_foods: int
    underweight_users: int
    recent_errors: int


class AdminFoodListResponse(BaseModel):
    items: list[dict]
    total: int
    limit: int
    offset: int


class AdminCategorySummaryResponse(BaseModel):
    items: list[dict]


class AdminMealPlanListResponse(BaseModel):
    items: list[dict]
    total: int
    limit: int
    offset: int


class AdminSystemErrorListResponse(BaseModel):
    items: list[dict]
    total: int
    limit: int
    offset: int


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
    image_alt_vi: str | None = None
    image_source_type: str | None = None
    image_verified: bool = False
    image_quality_note: str | None = None
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
    image_alt_vi: str | None = None
    image_source_type: str | None = None
    image_verified: bool | None = None
    image_quality_note: str | None = None
    source: str | None = None
    clean_category: str | None = None
    recommended_serving_g: float | None = Field(default=None, ge=0)
    serving_display: str | None = None
    menu_eligible: bool | None = None
    quality_flags: str | None = None


class FoodView(BaseModel):
    food_id: str
    name: str
    name_en: str | None = None
    image_url: str | None = None
    image_alt_vi: str | None = None
    image_source_type: str | None = None
    image_verified: bool = False
    image_quality_note: str | None = None
    image_badge: str | None = None
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
    items_per_meal: int | None = Field(default=None, ge=1, le=10)
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
    favorite_foods: list[str] = Field(default_factory=list)
    disliked_foods: list[str] = Field(default_factory=list)
    disliked_food_groups: list[str] = Field(default_factory=list)
    energy_tolerance_kcal: float | None = Field(default=80.0, ge=0)
    use_personalization: bool = False
    random_seed: int | None = None
    exclude_food_ids: list[str] = Field(default_factory=list)
    exclude_meal_plan_id: int | None = None
    min_protein_ratio: float = Field(default=0.90, ge=0.0, le=1.0)
    min_fat_ratio: float = Field(default=0.90, ge=0.0, le=1.0)
    macro_backtracking_attempts: int = Field(default=30, ge=0, le=200)
    save_user_data: bool = False

    @field_validator("favorite_foods", "disliked_foods", "disliked_food_groups", mode="before")
    @classmethod
    def normalize_food_list(cls, value: Any):
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []


class MealPlanRegenerateInput(BaseModel):
    userId: str | None = None
    date: str | None = None
    previousMealPlanId: int | str | None = None
    targetKcal: float | None = Field(default=None, gt=0)
    excludePreviousItems: bool = True

    weight: float | None = Field(default=None, ge=20, le=250)
    height: float | None = Field(default=None, ge=100, le=230)
    activity: str | None = None
    age: int | None = Field(default=None, ge=1, le=120)
    sex: str | None = None
    goal_type: str | None = None
    weight_gain_speed: str | None = None
    gain_speed: str | None = None
    meal_complexity: str | None = None
    items_per_meal: int | None = Field(default=None, ge=1, le=10)
    diet_style: str | None = None
    diet_type: str | None = None
    budget_level: str | None = None
    surplus_kcal: float | None = Field(default=None, ge=0)
    target_weight: float | None = Field(default=None, ge=20, le=250)
    protein_target: float | None = Field(default=None, ge=0)
    fat_target: float | None = Field(default=None, ge=0)
    carb_target: float | None = Field(default=None, ge=0)
    top_n: int = Field(default=10, ge=1, le=50)
    preferred_categories: list[str] = Field(default_factory=list)
    excluded_categories: list[str] = Field(default_factory=list)
    allergens: list[str] = Field(default_factory=list)
    favorite_foods: list[str] = Field(default_factory=list)
    disliked_foods: list[str] = Field(default_factory=list)
    disliked_food_groups: list[str] = Field(default_factory=list)
    randomSeed: int | None = None
    random_seed: int | None = None

    @field_validator("favorite_foods", "disliked_foods", "disliked_food_groups", mode="before")
    @classmethod
    def normalize_food_list(cls, value: Any):
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []


class NutritionTargetView(BaseModel):
    bmi: float
    bmi_category: str | None = None
    bmi_label: str | None = None
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
    validation: dict | None = None


class EligibilityCheckView(BaseModel):
    bmi: float | None = None
    weight_status: str
    bmi_category: str | None = None
    bmi_label: str | None = None
    eligible: bool
    reason: str
    message: str | None = None


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


class ProfileSummarySchema(BaseModel):
    age: int | None = None
    gender: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    bmi: float | None = None
    bmi_status: str | None = None
    bmi_category: str | None = None
    bmi_label: str | None = None
    medical_warning: bool | None = None
    target_weight_missing: bool | None = None
    suggested_stage_1_weight: float | None = None
    suggested_stage_2_weight: float | None = None

class NutritionTargetSchema(BaseModel):
    bmr: float | None = None
    tdee: float | None = None
    surplus: float | None = None
    ramp_up_week: int | None = None
    calorie_target: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    carbs_g: float | None = None
    calculation_source: str | None = None

class MealPlanMealSchema(BaseModel):
    meal_type: str
    target_kcal: float | None = None
    actual_kcal: int | None = None
    expected_items: int | None = None
    actual_items: int | None = None
    items: list[FoodItemView] = Field(default_factory=list)

class MealPlanSchema(BaseModel):
    id: int | None = None
    date: str | None = None
    status: str | None = None
    total_kcal: int | None = None
    total_protein_g: float | None = None
    total_fat_g: float | None = None
    total_carbs_g: float | None = None
    meal_item_count_summary: dict | None = None
    meals: list[MealPlanMealSchema] = Field(default_factory=list)

class ValidationSchema(BaseModel):
    status: str | None = None
    is_valid: bool
    isValid: bool | None = None
    warnings: list[str] = Field(default_factory=list)
    infos: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    reason: str | None = None
    targetKcal: float | None = None
    totalKcal: float | None = None
    kcalDiff: float | None = None
    kcalDiffPct: float | None = None
    target_kcal: float | None = None
    total_kcal: float | None = None
    kcal_diff: float | None = None
    kcal_diff_pct: float | None = None
    meal_item_count_summary: dict | None = None
    meal_fill_debug: list[dict] = Field(default_factory=list)
    recommendation_explanations: list[dict] = Field(default_factory=list)
    ml_enabled: bool | None = None
    ml_score_used: bool | None = None
    ml_score_weight: float | None = None

class RecommendationOutput(BaseModel):
    eligible: bool | None = None
    reason: str | None = None
    bmi: float | None = None
    bmi_category: str | None = None
    bmi_label: str | None = None
    message: str | None = None
    warning: str | None = None
    profile_summary: ProfileSummarySchema | None = None
    nutrition_target: NutritionTargetSchema | None = None
    meal_plan: MealPlanSchema | None = None
    validation: ValidationSchema | None = None
    target: NutritionTargetView | None = None
    target_kcal: float | None = None
    target_protein: float | None = None
    target_fat: float | None = None
    target_carbs: float | None = None
    items_per_meal: int | None = None
    kcal_delta: float | None = None
    macro_delta: dict | None = None
    profile_snapshot: dict | None = None
    meal_item_count_summary: dict | None = None
    recommendation_explanations: list[dict] = Field(default_factory=list)
    
    # Old fields for compatibility
    eligibility_check: EligibilityCheckView | None = None
    overall_assessment: OverallAssessmentView | None = None
    detected_issues: list[DetectedIssueView] = Field(default_factory=list)
    fixed_menu: list[FixedMenuMealView] = Field(default_factory=list)
    validation_rules_to_add: list[str] = Field(default_factory=list)
    top_recommendations: list[FoodItemView] = Field(default_factory=list)
    evaluation: EvaluationView | None = None


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
