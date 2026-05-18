from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.entities import Food, FoodCategory, FoodRating, User, UserProfileEntity
from app.repositories.food_repository import FoodRepository
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.user_repository import UserRepository
from app.services.weight_log_service import WeightLogService
from app.views.schemas import (
    AccountStatusUpdate,
    FoodCategoryCreate,
    FoodCategoryUpdate,
    FoodCreate,
    FoodRatingInput,
    FoodUpdate,
    UserProfileInput,
    UserUpdate,
)


def _dump_model(model, *, exclude_unset: bool = False) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_unset=exclude_unset)
    return model.dict(exclude_unset=exclude_unset)


def _parse_profile_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    return [part.strip() for part in text.replace(",", ";").split(";") if part.strip()]


def _serialize_profile_list(value: object) -> str:
    items = _parse_profile_list(value)
    return ";".join(items) if items else ""


class FoodService:
    @staticmethod
    def food_to_payload(food: Food) -> dict:
        name = food.dish_name_vi or food.name_vi or food.display_name or food.name or food.original_name or str(food.food_id)
        category = food.clean_category or food.category or "other"
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
            "name": name,
            "name_en": food.display_name or food.name or food.original_name,
            "image_url": food.image_url,
            "image_alt_vi": food.image_alt_vi,
            "image_source_type": source_type,
            "image_verified": is_verified,
            "image_quality_note": food.image_quality_note,
            "image_badge": image_badge,
            "category": category,
            "type": food.type,
            "source": food.source,
            "calories": float(food.kcal_per_serving_clean or food.calories or 0.0),
            "protein": float(food.protein_per_serving_clean or food.protein or 0.0),
            "fat": float(food.fat_per_serving_clean or food.fat or 0.0),
            "carbs": float(food.carbs_per_serving_clean or food.carbs or 0.0),
        }

    @staticmethod
    def category_to_payload(category: FoodCategory) -> dict:
        return {
            "id": category.id,
            "name": category.name,
            "display_name": category.display_name,
            "description": category.description,
            "source": category.source,
        }

    def list_foods(
        self,
        db: Session,
        query: str | None,
        category: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        rows, total = FoodRepository(db).list_foods(query, category, limit, offset)
        return {
            "items": [self.food_to_payload(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_food(self, db: Session, food_id: str) -> dict:
        food = FoodRepository(db).get_food(food_id)
        if food is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food not found")
        return self.food_to_payload(food)

    def create_food(self, db: Session, payload: FoodCreate) -> dict:
        values = _dump_model(payload)
        values["food_id"] = str(values["food_id"])
        values["category"] = str(values["category"]).strip().lower()
        food = FoodRepository(db).create_food(values)
        return self.food_to_payload(food)

    def update_food(self, db: Session, food_id: str, payload: FoodUpdate) -> dict:
        repository = FoodRepository(db)
        food = repository.get_food(food_id)
        if food is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food not found")
        values = _dump_model(payload, exclude_unset=True)
        if "category" in values and values["category"] is not None:
            values["category"] = str(values["category"]).strip().lower()
        food = repository.update_food(food, values)
        return self.food_to_payload(food)

    def delete_food(self, db: Session, food_id: str) -> dict[str, bool]:
        repository = FoodRepository(db)
        food = repository.get_food(food_id)
        if food is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food not found")
        repository.delete_food(food)
        return {"deleted": True}

    def list_categories(self, db: Session) -> dict:
        rows = FoodRepository(db).list_categories()
        return {"items": [self.category_to_payload(row) for row in rows]}

    def create_category(self, db: Session, payload: FoodCategoryCreate) -> dict:
        values = _dump_model(payload)
        values["name"] = str(values["name"]).strip().lower()
        category = FoodRepository(db).create_category(values)
        return self.category_to_payload(category)

    def update_category(self, db: Session, category_id: int, payload: FoodCategoryUpdate) -> dict:
        repository = FoodRepository(db)
        category = repository.get_category(category_id)
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        values = _dump_model(payload, exclude_unset=True)
        if "name" in values and values["name"] is not None:
            values["name"] = str(values["name"]).strip().lower()
        category = repository.update_category(category, values)
        return self.category_to_payload(category)

    def delete_category(self, db: Session, category_id: int) -> dict[str, bool]:
        repository = FoodRepository(db)
        category = repository.get_category(category_id)
        if category is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        repository.delete_category(category)
        return {"deleted": True}


class UserService:
    @staticmethod
    def user_to_payload(user: User) -> dict:
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": str(user.role or "USER").upper(),
            "status": str(getattr(user, "status", None) or ("ACTIVE" if user.is_active else "LOCKED")).upper(),
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(timespec="seconds"),
        }

    @staticmethod
    def profile_to_payload(profile: UserProfileEntity | None) -> dict | None:
        if profile is None:
            return None
        return {
            "weight_kg": profile.weight_kg,
            "height_cm": profile.height_cm,
            "age": profile.age,
            "sex": profile.sex,
            "gender": profile.gender or profile.sex,
            "activity_level": profile.activity_level,
            "surplus_kcal": profile.surplus_kcal,
            "favorite_foods": _parse_profile_list(profile.favorite_foods),
            "disliked_foods": _parse_profile_list(profile.disliked_foods),
            "disliked_food_groups": _parse_profile_list(profile.disliked_food_groups),
            "target_weight_kg": profile.target_weight_kg,
            "weight_gain_speed": profile.weight_gain_speed,
            "diet_type": profile.diet_type,
            "budget_level": profile.budget_level,
            "items_per_meal": profile.items_per_meal,
            "updated_at": profile.updated_at.isoformat(timespec="seconds"),
        }

    def get_me(self, db: Session, user: User) -> dict:
        db.expire_all()
        profile = (
            db.query(UserProfileEntity)
            .filter(UserProfileEntity.user_id == user.id)
            .populate_existing()
            .first()
        )
        print("[USERS ME WEIGHT CHECK]", {
            "current_user_id": user.id,
            "email": user.email,
            "profile_user_id": profile.user_id if profile else None,
            "weight_kg": profile.weight_kg if profile else None,
            "target_weight_kg": profile.target_weight_kg if profile else None,
            "height_cm": profile.height_cm if profile else None,
            "diet_type": profile.diet_type if profile else None,
            "items_per_meal": profile.items_per_meal if profile else None,
        })
        payload = self.user_to_payload(user)
        payload["profile"] = self.profile_to_payload(profile)
        print("[GET /users/me RESPONSE]", payload)
        return payload

    def update_me(self, db: Session, user: User, payload: UserUpdate) -> dict:
        values = _dump_model(payload, exclude_unset=True)
        update_values = {}
        if "email" in values and values["email"] is not None:
            update_values["email"] = str(values["email"]).strip().lower()
        if "full_name" in values:
            update_values["full_name"] = values["full_name"]
        if "password" in values and values["password"]:
            from app.core.security import hash_password, verify_password

            if not values.get("current_password") or not verify_password(
                str(values["current_password"]),
                user.password_hash,
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Current password is required to change password",
                )
            update_values["password_hash"] = hash_password(str(values["password"]))

        user = UserRepository(db).update_user(user, update_values)
        return self.get_me(db, user)

    def update_profile(self, db: Session, user: User, payload: UserProfileInput) -> dict:
        print("[PUT PROFILE] user_id=", user.id)
        print("[PUT PROFILE] raw payload=", payload)
        values = _dump_model(payload, exclude_unset=True)
        if payload.weight_kg is not None:
            values["weight_kg"] = payload.weight_kg
        print("[PUT PROFILE] update_data=", values)
        db.expire_all()

        print("[PROFILE UPDATE PAYLOAD WEIGHT]", {
            "current_user_id": user.id,
            "email": user.email,
            "payload_weight_kg": payload.weight_kg,
        })

        current_profile = (
            db.query(UserProfileEntity)
            .filter(UserProfileEntity.user_id == user.id)
            .populate_existing()
            .first()
        )
        
        target_weight = values.get("target_weight_kg")
        height = values.get("height_cm") or (getattr(current_profile, "height_cm", None) if current_profile else None)
        if target_weight is not None and height is not None and float(height) > 0:
            target_bmi = float(target_weight) / ((float(height) / 100.0) ** 2)
            if target_bmi >= 23.0:
                min_normal_weight = round(18.5 * ((float(height) / 100.0) ** 2), 1)
                max_normal_weight = round(22.9 * ((float(height) / 100.0) ** 2), 1)
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Cân nặng mục tiêu vượt vùng BMI bình thường theo chuẩn Châu Á. Vui lòng chọn mục tiêu trong khoảng {min_normal_weight}kg–{max_normal_weight}kg."
                )

        if "gender" in values and values["gender"] is not None:
            values["sex"] = values["gender"]
        elif "sex" in values and values["sex"] is not None:
            values["gender"] = values["sex"]

        if "favorite_foods" in values:
            normalized_favorite_foods = _parse_profile_list(values["favorite_foods"])
            print("[PUT PROFILE] normalized favorite_foods=", normalized_favorite_foods)
            values["favorite_foods"] = _serialize_profile_list(normalized_favorite_foods)
        if "disliked_foods" in values:
            normalized_disliked_foods = _parse_profile_list(values["disliked_foods"])
            print("[PUT PROFILE] normalized disliked_foods=", normalized_disliked_foods)
            values["disliked_foods"] = _serialize_profile_list(normalized_disliked_foods)
        if values.get("diet_style") and not values.get("diet_type"):
            values["diet_type"] = values["diet_style"]
        elif values.get("diet_type") and not values.get("diet_style"):
            values["diet_style"] = values["diet_type"]

        if "disliked_food_groups" in values:
            grp_list = _parse_profile_list(values["disliked_food_groups"])
            values["disliked_food_groups"] = _serialize_profile_list(grp_list)

        profile = UserRepository(db).upsert_profile(user.id, values)
        if payload.weight_kg is not None:
            profile.weight_kg = payload.weight_kg

        db.add(profile)
        db.commit()
        db.refresh(profile)

        print("[PROFILE UPDATE SAVED WEIGHT]", {
            "current_user_id": user.id,
            "saved_profile_user_id": profile.user_id,
            "saved_weight_kg": profile.weight_kg,
            "saved_target_weight_kg": profile.target_weight_kg,
            "updated_at": str(profile.updated_at) if profile.updated_at else None,
        })

        if profile.weight_kg is not None:
            WeightLogService().upsert_weight_log_from_profile_update(user, profile.weight_kg, db, source="profile_update")
            print("[WEIGHT LOG UPSERT FROM PROFILE]", {
                "user_id": user.id,
                "weight_kg": profile.weight_kg,
                "source": "profile_update"
            })

        db.expire_all()
        refreshed_profile = (
            db.query(UserProfileEntity)
            .filter(UserProfileEntity.user_id == user.id)
            .populate_existing()
            .first()
        )
        print("[PUT PROFILE] weight_kg=", getattr(refreshed_profile, "weight_kg", None))
        print("[PUT PROFILE] target_weight_kg=", getattr(refreshed_profile, "target_weight_kg", None))
        print("[PROFILE UPDATE CHECK]", {
            "user_id": user.id,
            "payload_diet_type": getattr(payload, "diet_type", None) or getattr(payload, "diet_style", None),
            "payload_budget_level": getattr(payload, "budget_level", None),
            "payload_items_per_meal": getattr(payload, "items_per_meal", None),
            "before_diet_type": getattr(current_profile, "diet_type", None) if current_profile else None,
            "before_budget_level": getattr(current_profile, "budget_level", None) if current_profile else None,
            "before_items_per_meal": getattr(current_profile, "items_per_meal", None) if current_profile else None,
            "after_diet_type": getattr(refreshed_profile, "diet_type", None) if refreshed_profile else None,
            "after_budget_level": getattr(refreshed_profile, "budget_level", None) if refreshed_profile else None,
            "after_items_per_meal": getattr(refreshed_profile, "items_per_meal", None) if refreshed_profile else None,
        })
        return self.profile_to_payload(refreshed_profile) or {}

    def admin_stats(self, db: Session) -> dict:
        repository = UserRepository(db)
        return {
            "total_users": repository.count_users(),
            "active_users": repository.count_active_users(),
            "admin_users": repository.count_admin_users(),
        }

    def list_users(self, db: Session, limit: int, offset: int) -> dict:
        repository = UserRepository(db)
        return {
            "items": [self.user_to_payload(user) for user in repository.list_users(limit, offset)],
            "total": repository.count_users(),
            "limit": limit,
            "offset": offset,
        }

    def update_account_status(
        self,
        db: Session,
        user_id: int,
        payload: AccountStatusUpdate,
    ) -> dict:
        repository = UserRepository(db)
        user = repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        values = _dump_model(payload, exclude_unset=True)
        if values.get("role") is not None and str(values["role"]).upper() not in {"USER", "ADMIN", "SUPER_ADMIN"}:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role")
        if values.get("role") is not None:
            values["role"] = str(values["role"]).upper()
        if values.get("status") is not None:
            values["status"] = str(values["status"]).upper()
            values["is_active"] = values["status"] == "ACTIVE"
        user = repository.update_user(user, values)
        return self.user_to_payload(user)


class InteractionService:
    def __init__(self) -> None:
        self.food_service = FoodService()

    def list_favorites(self, db: Session, user: User) -> dict:
        rows = InteractionRepository(db).list_favorites(user.id)
        return {"items": [self.food_service.food_to_payload(row) for row in rows]}

    def add_favorite(self, db: Session, user: User, food_id: str) -> dict:
        if FoodRepository(db).get_food(food_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food not found")
        InteractionRepository(db).add_favorite(user.id, food_id)
        return {"food_id": str(food_id), "is_favorite": True}

    def remove_favorite(self, db: Session, user: User, food_id: str) -> dict:
        removed = InteractionRepository(db).remove_favorite(user.id, food_id)
        return {"food_id": str(food_id), "is_favorite": False, "removed": removed}

    def rate_food(self, db: Session, user: User, food_id: str, payload: FoodRatingInput) -> dict:
        if FoodRepository(db).get_food(food_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food not found")
        row = InteractionRepository(db).upsert_rating(user.id, food_id, payload.rating)
        return self.rating_to_payload(row)

    @staticmethod
    def rating_to_payload(row: FoodRating) -> dict:
        return {
            "food_id": row.food_id,
            "rating": row.rating,
            "updated_at": row.updated_at.isoformat(timespec="seconds"),
        }
