from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import ErrorLog, Food, FoodLog, Meal, MealPlan, RecommendationRequest, User, UserProfileEntity, WeightLog
from app.services.food_service import _parse_profile_list
from app.services.nutrition_calculation_service import asian_bmi_label, classify_asian_bmi
from app.services.recommender_service import RecommenderService
from app.views.schemas import FoodUpdate, RecommendationInput


CANONICAL_CATEGORIES = [
    "starch_grain",
    "starch_tuber",
    "protein_meat",
    "protein_seafood",
    "plant_protein",
    "egg",
    "vegetable",
    "fruit",
    "dairy",
    "healthy_fat_nuts",
    "drink_natural",
    "dessert_sweets",
    "other",
]


def _dump_model(model, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_unset=exclude_unset)
    return model.dict(exclude_unset=exclude_unset)


def _bmi(weight_kg: float | None, height_cm: float | None) -> float | None:
    if not weight_kg or not height_cm:
        return None
    height_m = float(height_cm) / 100
    if height_m <= 0:
        return None
    return round(float(weight_kg) / (height_m * height_m), 1)


def _bmi_category(bmi: float | None) -> str | None:
    if bmi is None:
        return None
    return classify_asian_bmi(bmi)


class AdminService:
    @staticmethod
    def _user_payload(user: User) -> dict:
        profile = getattr(user, "profile", None)
        bmi = _bmi(getattr(profile, "weight_kg", None), getattr(profile, "height_cm", None))
        category = _bmi_category(bmi)
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": str(user.role or "USER").upper(),
            "status": str(getattr(user, "status", None) or ("ACTIVE" if user.is_active else "LOCKED")).upper(),
            "is_active": bool(user.is_active),
            "created_at": user.created_at.isoformat(timespec="seconds"),
            "bmi": bmi,
            "bmi_category": category,
            "bmi_label": asian_bmi_label(category),
            "weight_kg": getattr(profile, "weight_kg", None),
            "target_weight_kg": getattr(profile, "target_weight_kg", None),
        }

    @staticmethod
    def _food_payload(food: Food) -> dict:
        is_verified = bool(food.image_verified)
        source_type = food.image_source_type or "placeholder"
        is_placeholder = (source_type == "placeholder") or not is_verified
        image_badge = (
            "Cần duyệt"
            if source_type == "pexels" and not is_verified
            else "Ảnh thật"
            if is_verified and not is_placeholder
            else "Ảnh minh họa"
        )
        return {
            "food_id": str(food.food_id),
            "name": food.dish_name_vi or food.name_vi or food.display_name or food.name or food.original_name or str(food.food_id),
            "category": food.clean_category or food.category or "other",
            "calories": float(food.kcal_per_serving_clean or food.calories or 0.0),
            "protein": float(food.protein_per_serving_clean or food.protein or 0.0),
            "fat": float(food.fat_per_serving_clean or food.fat or 0.0),
            "carbs": float(food.carbs_per_serving_clean or food.carbs or 0.0),
            "serving": food.serving_display,
            "recommended_serving_g": food.recommended_serving_g,
            "menu_eligible": bool(food.menu_eligible),
            "image_url": food.image_url,
            "image_alt_vi": food.image_alt_vi,
            "image_source_type": source_type,
            "image_verified": is_verified,
            "image_quality_note": food.image_quality_note,
            "image_badge": image_badge,
            "quality_flags": food.quality_flags,
        }

    def overview(self, db: Session) -> dict:
        today = date.today()
        recent_cutoff = datetime.utcnow() - timedelta(days=7)
        underweight_users = 0
        for profile in db.scalars(select(UserProfileEntity).where(UserProfileEntity.weight_kg.is_not(None), UserProfileEntity.height_cm.is_not(None))):
            bmi = _bmi(profile.weight_kg, profile.height_cm)
            if bmi is not None and bmi < 18.5:
                underweight_users += 1
        return {
            "total_users": int(db.scalar(select(func.count(User.id))) or 0),
            "new_users_today": int(db.scalar(select(func.count(User.id)).where(func.date(User.created_at) == today)) or 0),
            "total_meal_plans": int(db.scalar(select(func.count(MealPlan.id))) or 0),
            "total_foods": int(db.scalar(select(func.count(Food.food_id))) or 0),
            "eligible_foods": int(db.scalar(select(func.count(Food.food_id)).where(Food.menu_eligible.is_(True))) or 0),
            "underweight_users": underweight_users,
            "recent_errors": int(db.scalar(select(func.count(ErrorLog.id)).where(ErrorLog.created_at >= recent_cutoff, ErrorLog.status != "RESOLVED")) or 0),
        }

    def list_users(self, db: Session, q: str | None, status_filter: str | None, bmi_category: str | None, limit: int, offset: int) -> dict:
        statement = select(User).options(selectinload(User.profile))
        filters = []
        if q:
            filters.append(User.email.ilike(f"%{q.strip()}%"))
        if status_filter:
            filters.append(func.upper(User.status) == status_filter.strip().upper())
        for item in filters:
            statement = statement.where(item)
        rows = list(db.scalars(statement.order_by(User.created_at.desc())).unique())
        payload = [self._user_payload(user) for user in rows]
        if bmi_category:
            normalized = bmi_category.strip().lower()
            payload = [item for item in payload if str(item.get("bmi_category") or "").lower() == normalized]
        total = len(payload)
        return {"items": payload[offset : offset + limit], "total": total, "limit": limit, "offset": offset}

    def user_detail(self, db: Session, user_id: int) -> dict:
        user = db.scalar(select(User).options(selectinload(User.profile), selectinload(User.weight_logs)).where(User.id == user_id))
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        profile = user.profile
        meal_plans = list(
            db.scalars(select(MealPlan).where(MealPlan.user_id == user_id).order_by(MealPlan.created_at.desc()).limit(5))
        )
        food_logs = list(
            db.scalars(select(FoodLog).where(FoodLog.user_id == user_id).order_by(FoodLog.log_date.desc()).limit(5))
        )
        payload = self._user_payload(user)
        payload["profile"] = None if profile is None else {
            "weight_kg": profile.weight_kg,
            "height_cm": profile.height_cm,
            "age": profile.age,
            "sex": profile.sex,
            "gender": profile.gender or profile.sex,
            "activity_level": profile.activity_level,
            "favorite_foods": _parse_profile_list(profile.favorite_foods),
            "disliked_foods": _parse_profile_list(profile.disliked_foods),
            "disliked_food_groups": _parse_profile_list(profile.disliked_food_groups),
            "target_weight_kg": profile.target_weight_kg,
            "weight_gain_speed": profile.weight_gain_speed,
            "diet_type": profile.diet_type,
            "budget_level": profile.budget_level,
            "items_per_meal": profile.items_per_meal,
        }
        payload["weight_logs"] = [
            {"id": row.id, "weight_kg": row.weight_kg, "log_date": row.log_date.isoformat(), "note": row.note}
            for row in sorted(user.weight_logs, key=lambda item: item.log_date, reverse=True)[:20]
        ]
        payload["meal_plans"] = [self._meal_plan_payload(row) for row in meal_plans]
        payload["food_logs"] = [
            {
                "id": row.id,
                "log_date": row.log_date.isoformat(),
                "consumed_kcal": row.consumed_kcal,
                "consumed_protein": row.consumed_protein,
                "consumed_fat": row.consumed_fat,
                "consumed_carbs": row.consumed_carbs,
            }
            for row in food_logs
        ]
        return payload

    def update_user_status(self, db: Session, user_id: int, values: dict) -> dict:
        user = db.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        status_value = values.get("status")
        if status_value is None and "is_active" in values:
            status_value = "ACTIVE" if values["is_active"] else "LOCKED"
        if status_value is not None:
            status_value = str(status_value).upper()
            if status_value not in {"ACTIVE", "LOCKED"}:
                raise HTTPException(status_code=422, detail="Invalid status")
            user.status = status_value
            user.is_active = status_value == "ACTIVE"
        if values.get("role") is not None:
            role = str(values["role"]).upper()
            if role not in {"USER", "ADMIN", "SUPER_ADMIN"}:
                raise HTTPException(status_code=422, detail="Invalid role")
            user.role = role
        db.commit()
        db.refresh(user)
        return self._user_payload(user)

    def list_foods(
        self,
        db: Session,
        q: str | None,
        category: str | None,
        menu_eligible: bool | None,
        missing_image: bool,
        has_quality_flags: bool,
        image_status: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        statement = select(Food)
        count_statement = select(func.count(Food.food_id))
        filters = []
        if q:
            like_text = f"%{q.strip()}%"
            filters.append(or_(Food.name.ilike(like_text), Food.name_vi.ilike(like_text), Food.dish_name_vi.ilike(like_text), Food.display_name.ilike(like_text)))
        if category:
            filters.append(or_(Food.category == category.strip().lower(), Food.clean_category == category.strip().lower()))
        if menu_eligible is not None:
            filters.append(Food.menu_eligible.is_(menu_eligible))
        if missing_image:
            filters.append(or_(Food.image_url.is_(None), Food.image_url == ""))
        if has_quality_flags:
            filters.append(Food.quality_flags.is_not(None), Food.quality_flags != "")
        if image_status == "pexels_pending":
            filters.append(Food.image_source_type == "pexels")
            filters.append(or_(Food.image_verified.is_(False), Food.image_verified.is_(None)))
        elif image_status == "verified_real":
            filters.append(Food.image_source_type == "real")
            filters.append(Food.image_verified.is_(True))
        for item in filters:
            statement = statement.where(item)
            count_statement = count_statement.where(item)
        total = int(db.scalar(count_statement) or 0)
        rows = list(db.scalars(statement.order_by(Food.food_id.asc()).offset(offset).limit(limit)))
        return {"items": [self._food_payload(row) for row in rows], "total": total, "limit": limit, "offset": offset}

    def get_food(self, db: Session, food_id: str) -> dict:
        food = db.get(Food, str(food_id))
        if food is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food not found")
        return self._food_payload(food)

    def update_food(self, db: Session, food_id: str, payload: FoodUpdate) -> dict:
        food = db.get(Food, str(food_id))
        if food is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food not found")
        values = _dump_model(payload, exclude_unset=True)
        for key, value in values.items():
            if hasattr(food, key):
                setattr(food, key, value)
        db.commit()
        db.refresh(food)
        return self._food_payload(food)

    def category_summary(self, db: Session) -> dict:
        rows = db.execute(
            select(func.coalesce(Food.clean_category, Food.category, "other"), func.count(Food.food_id))
            .group_by(func.coalesce(Food.clean_category, Food.category, "other"))
        ).all()
        counts = {str(name or "other"): int(count or 0) for name, count in rows}
        return {"items": [{"category": category, "count": counts.get(category, 0)} for category in CANONICAL_CATEGORIES]}

    def recommendation_test(self, db: Session, admin_user: User, payload: RecommendationInput) -> dict:
        payload.save_user_data = False
        result = RecommenderService().generate_recommendations(payload, db, admin_user, persist=False)
        meal_plan = result.get("meal_plan") or {}
        target = result.get("nutrition_target") or {}
        validation = result.get("validation") or {}
        meal_plan.pop("id", None)
        return {
            **result,
            "target_kcal": target.get("calorie_target"),
            "target_protein": target.get("protein_g"),
            "target_fat": target.get("fat_g"),
            "target_carbs": target.get("carbs_g"),
            "items_per_meal": payload.items_per_meal,
            "kcal_delta": validation.get("kcalDiff") or validation.get("kcal_diff"),
            "macro_delta": {
                "protein": (meal_plan.get("total_protein_g") or 0) - (target.get("protein_g") or 0),
                "fat": (meal_plan.get("total_fat_g") or 0) - (target.get("fat_g") or 0),
                "carbs": (meal_plan.get("total_carbs_g") or 0) - (target.get("carbs_g") or 0),
            },
        }

    @staticmethod
    def _meal_plan_payload(row: MealPlan) -> dict:
        return {
            "id": row.id,
            "user_id": row.user_id,
            "plan_date": row.plan_date.isoformat() if row.plan_date else None,
            "target_kcal": row.target_kcal,
            "total_kcal": row.total_kcal,
            "status": row.status,
            "created_at": row.created_at.isoformat(timespec="seconds"),
        }

    def list_meal_plans(self, db: Session, q: str | None, status_filter: str | None, only_errors: bool, limit: int, offset: int) -> dict:
        statement = select(MealPlan, User.email).join(User, User.id == MealPlan.user_id)
        count_statement = select(func.count(MealPlan.id)).join(User, User.id == MealPlan.user_id)
        filters = []
        if q:
            filters.append(User.email.ilike(f"%{q.strip()}%"))
        if status_filter:
            filters.append(MealPlan.status == status_filter.strip())
        if only_errors:
            filters.append(MealPlan.status.in_(["invalid", "error", "failed", "major_adjustment"]))
        for item in filters:
            statement = statement.where(item)
            count_statement = count_statement.where(item)
        total = int(db.scalar(count_statement) or 0)
        rows = db.execute(statement.order_by(MealPlan.created_at.desc()).offset(offset).limit(limit)).all()
        return {
            "items": [{**self._meal_plan_payload(plan), "user_email": email} for plan, email in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def meal_plan_detail(self, db: Session, meal_plan_id: int) -> dict:
        row = db.scalar(select(MealPlan).options(selectinload(MealPlan.meals).selectinload(Meal.items)).where(MealPlan.id == meal_plan_id))
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal plan not found")
        payload = self._meal_plan_payload(row)
        payload["meals"] = [
            {
                "id": meal.id,
                "meal_type": meal.meal_type,
                "total_kcal": meal.total_kcal,
                "items": [
                    {
                        "id": item.id,
                        "food_id": item.food_id,
                        "name": item.reason,
                        "kcal": item.kcal,
                        "protein": item.protein,
                        "fat": item.fat,
                        "carbs": item.carbs,
                        "serving_display": item.serving_display,
                    }
                    for item in meal.items
                ],
            }
            for meal in sorted(row.meals, key=lambda item: item.meal_order)
        ]
        return payload

    def list_system_errors(self, db: Session, limit: int, offset: int) -> dict:
        total = int(db.scalar(select(func.count(ErrorLog.id))) or 0)
        rows = db.execute(
            select(ErrorLog, User.email)
            .outerjoin(User, User.id == ErrorLog.user_id)
            .order_by(ErrorLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return {
            "items": [
                {
                    "id": error.id,
                    "time": error.created_at.isoformat(timespec="seconds"),
                    "endpoint": error.endpoint,
                    "user_email": email,
                    "error_type": error.error_type,
                    "message": error.message,
                    "status": error.status,
                }
                for error, email in rows
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def resolve_error(self, db: Session, error_id: int) -> dict:
        row = db.get(ErrorLog, error_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Error log not found")
        row.status = "RESOLVED"
        db.commit()
        return {"id": row.id, "status": row.status}
