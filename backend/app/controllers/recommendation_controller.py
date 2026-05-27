from __future__ import annotations

import logging
import time

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import User
from app.services.recommender_service import RecommenderService
from app.views.schemas import (
    MealPlanRegenerateInput,
    RecommendationHistoryDetail,
    RecommendationHistoryResponse,
    RecommendationInput,
    RecommendationOutput,
)

logger = logging.getLogger(__name__)


class RecommendationController:
    def __init__(self) -> None:
        self.service = RecommenderService()

    def _normalize_recommendation_output(self, result: dict) -> dict:
        if not isinstance(result, dict):
            return result

        eligibility = result.get("eligibility_check")
        if not isinstance(eligibility, dict):
            eligibility = {}

        profile_snapshot = result.get("profile_snapshot")
        if not isinstance(profile_snapshot, dict):
            profile_snapshot = {}

        weight_status = (
            eligibility.get("weight_status")
            or result.get("weight_status")
            or profile_snapshot.get("weight_status")
            or "normal"
        )

        eligibility.setdefault("eligible", True)
        eligibility.setdefault("reason", "passed eligibility check")
        eligibility["weight_status"] = weight_status
        result["eligibility_check"] = eligibility
        return result

    def create_recommendation(
        self,
        payload: RecommendationInput,
        db: Session,
        user: User,
    ) -> RecommendationOutput:
        result = self.service.generate_recommendations(payload, db, user)
        result = self._normalize_recommendation_output(result)
        logger.info("[RECOMMENDATION OUTPUT ELIGIBILITY CHECK] %s", result.get("eligibility_check"))
        return RecommendationOutput(**result)

    def regenerate_meal_plan(
        self,
        payload: MealPlanRegenerateInput,
        db: Session,
        user: User,
    ) -> RecommendationOutput:
        start = time.perf_counter()
        try:
            print("[REGENERATE INGREDIENT PAYLOAD CHECK]", {
                "available_ingredients": getattr(payload, "available_ingredients", None),
                "ingredients": getattr(payload, "ingredients", None),
                "generation_seed": getattr(payload, "generation_seed", None)
                or getattr(payload, "random_seed", None)
                or getattr(payload, "randomSeed", None),
            }, flush=True)
        except Exception:
            logger.warning("[REGENERATE INGREDIENT PAYLOAD CHECK FAILED]", exc_info=True)
        result = self.service.regenerate_meal_plan(payload, db, user)
        logger.info(
            "[REGENERATE CONTROLLER TIMING] %s",
            {"service_ms": round((time.perf_counter() - start) * 1000.0, 2)},
        )
        result = self._normalize_recommendation_output(result)
        logger.info("[RECOMMENDATION OUTPUT ELIGIBILITY CHECK] %s", result.get("eligibility_check"))
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
