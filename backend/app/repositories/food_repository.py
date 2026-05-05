from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.entities import Food, FoodCategory


class FoodRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_food(self, food_id: str) -> Food | None:
        return self.db.get(Food, str(food_id))

    def list_foods(
        self,
        query_text: str | None = None,
        category: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Food], int]:
        statement = select(Food)
        count_statement = select(func.count(Food.food_id))

        filters = []
        if query_text:
            like_text = f"%{query_text.strip()}%"
            filters.append(or_(Food.name.ilike(like_text), Food.name_vi.ilike(like_text)))
        if category:
            filters.append(Food.category == category.strip().lower())

        for item in filters:
            statement = statement.where(item)
            count_statement = count_statement.where(item)

        total = int(self.db.scalar(count_statement) or 0)
        rows = list(
            self.db.scalars(
                statement.order_by(Food.name.asc()).offset(offset).limit(limit)
            )
        )
        return rows, total

    def create_food(self, values: dict) -> Food:
        food = Food(**values)
        self.db.add(food)
        self.db.commit()
        self.db.refresh(food)
        return food

    def update_food(self, food: Food, values: dict) -> Food:
        for key, value in values.items():
            setattr(food, key, value)
        self.db.commit()
        self.db.refresh(food)
        return food

    def delete_food(self, food: Food) -> None:
        self.db.delete(food)
        self.db.commit()

    def get_category(self, category_id: int) -> FoodCategory | None:
        return self.db.get(FoodCategory, category_id)

    def get_category_by_name(self, name: str) -> FoodCategory | None:
        return self.db.scalar(
            select(FoodCategory).where(FoodCategory.name == name.strip().lower())
        )

    def list_categories(self) -> list[FoodCategory]:
        return list(self.db.scalars(select(FoodCategory).order_by(FoodCategory.name.asc())))

    def create_category(self, values: dict) -> FoodCategory:
        category = FoodCategory(**values)
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def update_category(self, category: FoodCategory, values: dict) -> FoodCategory:
        for key, value in values.items():
            setattr(category, key, value)
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete_category(self, category: FoodCategory) -> None:
        self.db.delete(category)
        self.db.commit()
