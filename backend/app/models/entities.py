from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    profile: Mapped["UserProfileEntity | None"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    weight_logs: Mapped[list["WeightLog"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    recommendations: Mapped[list["RecommendationRequest"]] = relationship(back_populates="user")


class UserProfileEntity(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(20), nullable=True)
    activity_level: Mapped[str] = mapped_column(String(50), default="moderate", nullable=False)
    surplus_kcal: Mapped[float | None] = mapped_column(Float, nullable=True)
    favorite_foods: Mapped[str | None] = mapped_column(Text, nullable=True)
    disliked_foods: Mapped[str | None] = mapped_column(Text, nullable=True)
    disliked_food_groups: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_gain_speed: Mapped[str | None] = mapped_column(String(50), nullable=True)
    diet_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    budget_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    items_per_meal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="profile")


class WeightLog(Base):
    __tablename__ = "weight_logs"
    __table_args__ = (UniqueConstraint("user_id", "log_date", name="unique_user_weight_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_chart_milestone: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="weight_logs")


class FoodCategory(Base):
    __tablename__ = "food_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)


class Food(Base):
    __tablename__ = "foods"

    food_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    calories: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs: Mapped[float | None] = mapped_column(Float, nullable=True)
    name_vi: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    original_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    dish_name_vi: Mapped[str | None] = mapped_column(Text, nullable=True)
    clean_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    food_group_vi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meal_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recommended_serving_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    serving_display: Mapped[str | None] = mapped_column(String(255), nullable=True)
    kcal_per_100g_clean: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_per_100g_clean: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_per_100g_clean: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_per_100g_clean: Mapped[float | None] = mapped_column(Float, nullable=True)
    kcal_per_serving_clean: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_per_serving_clean: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_per_serving_clean: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_per_serving_clean: Mapped[float | None] = mapped_column(Float, nullable=True)
    menu_eligible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quality_flags: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_alt_vi: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_source_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    image_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    image_quality_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)


class UserFavoriteFood(Base):
    __tablename__ = "user_favorite_foods"
    __table_args__ = (UniqueConstraint("user_id", "food_id", name="uq_user_favorite_food"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    food_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class FoodRating(Base):
    __tablename__ = "food_ratings"
    __table_args__ = (UniqueConstraint("user_id", "food_id", name="uq_user_food_rating"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    food_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class RecommendationRequest(Base):
    __tablename__ = "recommendation_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    height_cm: Mapped[float] = mapped_column(Float, nullable=False)
    activity_level: Mapped[str] = mapped_column(String(50), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(20), nullable=True)
    surplus_kcal: Mapped[float | None] = mapped_column(Float, nullable=True)

    preferred_categories: Mapped[str | None] = mapped_column(Text, nullable=True)
    excluded_categories: Mapped[str | None] = mapped_column(Text, nullable=True)

    target_calories: Mapped[float] = mapped_column(Float, nullable=False)
    bmr: Mapped[float | None] = mapped_column(Float, nullable=True)
    tdee: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommended_calories: Mapped[float] = mapped_column(Float, nullable=False)
    absolute_error: Mapped[float] = mapped_column(Float, nullable=False)
    relative_error_pct: Mapped[float] = mapped_column(Float, nullable=False)
    precision_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped[User | None] = relationship(back_populates="recommendations")
    meal_plans: Mapped[list["MealPlan"]] = relationship(
        back_populates="recommendation_request",
        cascade="all, delete-orphan",
    )


class MealPlan(Base):
    __tablename__ = "meal_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    recommendation_request_id: Mapped[int | None] = mapped_column(ForeignKey("recommendation_requests.id"), nullable=True, index=True)
    plan_date: Mapped[date | None] = mapped_column(Date, nullable=True, default=date.today)
    target_kcal: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    target_protein: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    target_fat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    target_carbs: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_kcal: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_protein: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_fat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_carbs: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    recommendation_request: Mapped[RecommendationRequest | None] = relationship(back_populates="meal_plans")
    meals: Mapped[list["Meal"]] = relationship(back_populates="meal_plan", cascade="all, delete-orphan")


class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meal_plan_id: Mapped[int] = mapped_column(ForeignKey("meal_plans.id"), nullable=False, index=True)
    meal_type: Mapped[str] = mapped_column(String(30), nullable=False)
    meal_name_vi: Mapped[str | None] = mapped_column(String(100), nullable=True)
    meal_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_kcal: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_protein: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_fat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_carbs: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    balance_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    meal_plan: Mapped[MealPlan] = relationship(back_populates="meals")
    items: Mapped[list["MealPlanItem"]] = relationship(back_populates="meal", cascade="all, delete-orphan")


class MealPlanItem(Base):
    __tablename__ = "meal_plan_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meal_id: Mapped[int] = mapped_column(ForeignKey("meals.id"), nullable=False, index=True)
    food_id: Mapped[str] = mapped_column(String(100), nullable=False)
    meal_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    quantity_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    kcal: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    protein: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fat: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    carbs: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    serving_display: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_badge: Mapped[str | None] = mapped_column(String(100), nullable=True)
    item_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    meal: Mapped[Meal | None] = relationship(back_populates="items")
    log_items: Mapped[list["FoodLogItem"]] = relationship(back_populates="meal_plan_item")


class FoodLog(Base):
    __tablename__ = "food_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    log_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    consumed_kcal: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    consumed_protein: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    consumed_fat: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    consumed_carbs: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    items: Mapped[list["FoodLogItem"]] = relationship(back_populates="food_log", cascade="all, delete-orphan")


class FoodLogItem(Base):
    __tablename__ = "food_log_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    food_log_id: Mapped[int] = mapped_column(ForeignKey("food_logs.id"), nullable=False, index=True)
    food_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    meal_plan_item_id: Mapped[int | None] = mapped_column(ForeignKey("meal_plan_items.id"), nullable=True, index=True)
    meal_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="eaten", nullable=False)
    custom_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    kcal: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    protein: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    fat: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    carbs: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    food_log: Mapped[FoodLog] = relationship(back_populates="items")
    meal_plan_item: Mapped[MealPlanItem | None] = relationship(back_populates="log_items")
