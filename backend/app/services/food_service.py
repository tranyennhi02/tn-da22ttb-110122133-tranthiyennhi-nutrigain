from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.entities import Food, FoodCategory, FoodRating, User, UserProfileEntity
from app.repositories.food_repository import FoodRepository
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.user_repository import UserRepository
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


def _serialize_profile_list(value: object) -> str | None:
    items = _parse_profile_list(value)
    return ";".join(items) if items else None


class FoodService:
    @staticmethod
    def food_to_payload(food: Food) -> dict:
        name = food.dish_name_vi or food.name_vi or food.display_name or food.name or food.original_name or str(food.food_id)
        category = food.clean_category or food.category or "other"
        return {
            "food_id": str(food.food_id),
            "name": name,
            "name_en": food.display_name or food.name or food.original_name,
            "image_url": food.image_url,
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
            "role": user.role,
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
            "activity_level": profile.activity_level,
            "surplus_kcal": profile.surplus_kcal,
            "disliked_foods": _parse_profile_list(profile.disliked_foods),
            "disliked_food_groups": _parse_profile_list(profile.disliked_food_groups),
            "updated_at": profile.updated_at.isoformat(timespec="seconds"),
        }

    def get_me(self, user: User) -> dict:
        payload = self.user_to_payload(user)
        payload["profile"] = self.profile_to_payload(user.profile)
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
        return self.get_me(user)

    def update_profile(self, db: Session, user: User, payload: UserProfileInput) -> dict:
        values = _dump_model(payload, exclude_unset=True)
        if "disliked_foods" in values:
            values["disliked_foods"] = _serialize_profile_list(values["disliked_foods"])
        if "disliked_food_groups" in values:
            values["disliked_food_groups"] = _serialize_profile_list(values["disliked_food_groups"])
        profile = UserRepository(db).upsert_profile(user.id, values)
        return self.profile_to_payload(profile) or {}

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
        if values.get("role") is not None and values["role"] not in {"user", "admin"}:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role")
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
