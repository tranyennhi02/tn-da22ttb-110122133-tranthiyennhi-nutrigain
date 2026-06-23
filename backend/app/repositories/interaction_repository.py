from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Food, FoodRating, UserFavoriteFood


class InteractionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_favorites(self, user_id: int) -> list[Food]:
        query = (
            select(Food)
            .join(UserFavoriteFood, UserFavoriteFood.food_id == Food.food_id)
            .where(UserFavoriteFood.user_id == user_id)
            .order_by(UserFavoriteFood.created_at.desc())
        )
        return list(self.db.scalars(query))

    def favorite_food_ids(self, user_id: int) -> set[str]:
        rows = self.db.scalars(
            select(UserFavoriteFood.food_id).where(UserFavoriteFood.user_id == user_id)
        )
        return {str(food_id) for food_id in rows}

    def add_favorite(self, user_id: int, food_id: str) -> UserFavoriteFood:
        existing = self.db.scalar(
            select(UserFavoriteFood).where(
                UserFavoriteFood.user_id == user_id,
                UserFavoriteFood.food_id == str(food_id),
            )
        )
        if existing is not None:
            return existing

        favorite = UserFavoriteFood(user_id=user_id, food_id=str(food_id))
        self.db.add(favorite)
        self.db.commit()
        self.db.refresh(favorite)
        return favorite

    def remove_favorite(self, user_id: int, food_id: str) -> bool:
        existing = self.db.scalar(
            select(UserFavoriteFood).where(
                UserFavoriteFood.user_id == user_id,
                UserFavoriteFood.food_id == str(food_id),
            )
        )
        if existing is None:
            return False
        self.db.delete(existing)
        self.db.commit()
        return True

    def ratings_by_user(self, user_id: int) -> dict[str, int]:
        rows = self.db.execute(
            select(FoodRating.food_id, FoodRating.rating).where(FoodRating.user_id == user_id)
        ).all()
        return {str(food_id): int(rating) for food_id, rating in rows}

    def get_rating(self, user_id: int, food_id: str) -> FoodRating | None:
        return self.db.scalar(
            select(FoodRating).where(
                FoodRating.user_id == user_id,
                FoodRating.food_id == str(food_id),
            )
        )

    def upsert_rating(self, user_id: int, food_id: str, rating: int) -> FoodRating:
        row = self.get_rating(user_id, food_id)
        if row is None:
            row = FoodRating(user_id=user_id, food_id=str(food_id), rating=int(rating))
            self.db.add(row)
        else:
            row.rating = int(rating)
        self.db.commit()
        self.db.refresh(row)
        return row
