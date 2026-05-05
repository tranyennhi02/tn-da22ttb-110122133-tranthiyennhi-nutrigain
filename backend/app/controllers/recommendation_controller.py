from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import User
from app.services.recommender_service import RecommenderService
from app.views.schemas import (
    RecommendationHistoryDetail,
    RecommendationHistoryResponse,
    RecommendationInput,
    RecommendationOutput,
)


class RecommendationController:
    def __init__(self) -> None:
        self.service = RecommenderService()

    def create_recommendation(
        self,
        payload: RecommendationInput,
        db: Session,
        user: User,
    ) -> RecommendationOutput:
        result = self.service.generate_recommendations(payload, db, user)
        return RecommendationOutput(**result)

    def list_history(
        self,
        db: Session,
        user: User,
        limit: int,
        period: str = "all",
    ) -> RecommendationHistoryResponse:
        result = self.service.get_history(db, user=user, limit=limit, period=period)
        return RecommendationHistoryResponse(**result)

    def history_detail(self, db: Session, user: User, request_id: int) -> RecommendationHistoryDetail:
        result = self.service.get_history_detail(db, user=user, request_id=request_id)
        return RecommendationHistoryDetail(**result)

    def today_meal_plan(self, db: Session, user: User) -> dict:
        return self.service.get_today_meal_plan(db, user=user)

    def check_in_meal_plan_item(
        self,
        db: Session,
        user: User,
        meal_plan_item_id: int,
        eaten: bool,
        serving_grams: float | None = None,
    ) -> dict:
        return self.service.check_in_meal_plan_item(
            db,
            user=user,
            meal_plan_item_id=meal_plan_item_id,
            eaten=eaten,
            serving_grams=serving_grams,
        )


controller = RecommendationController()


def get_db_dependency():
    return Depends(get_db)
