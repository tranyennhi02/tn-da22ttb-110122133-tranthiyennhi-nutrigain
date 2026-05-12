from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import Base
from app.models.entities import User, UserProfileEntity, WeightLog
from app.services.food_service import UserService
from app.services.recommender_service import (
    BMI_NOT_UNDERWEIGHT,
    BMI_SCOPE_MESSAGE,
    RecommenderService,
)
from app.services import weight_log_service as weight_log_module
from app.services.weight_log_service import WeightLogService
from app.views.schemas import RecommendationInput, UserProfileInput


def assert_close(actual: float | None, expected: float, tolerance: float = 0.05) -> None:
    assert actual is not None, f"expected {expected}, got None"
    assert abs(float(actual) - expected) <= tolerance, f"expected {expected}, got {actual}"


def main() -> None:
    fixed_now_vn = datetime(2026, 5, 11, 9, 30, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
    original_now_vn = weight_log_module.now_vn
    weight_log_module.now_vn = lambda: fixed_now_vn

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    today_vn = fixed_now_vn.date()

    user = User(
        email="sync-smoke@example.com",
        password_hash="test",
        full_name="Sync Smoke",
    )
    db.add(user)
    db.flush()
    profile = UserProfileEntity(
        user_id=user.id,
        weight_kg=37,
        height_cm=167,
        age=24,
        sex="female",
        activity_level="moderate",
        favorite_foods="banana;milk",
        disliked_foods="ga;thit ga;uc ga;chicken;chicken breast;turkey;ga tay",
        target_weight_kg=56,
    )
    db.add(profile)
    db.commit()
    user = db.get(User, user.id)

    service = UserService()
    updated_profile = service.update_profile(
        db,
        user,
        UserProfileInput(favorite_foods=[], disliked_foods=[]),
    )
    assert updated_profile["favorite_foods"] == [], updated_profile
    assert updated_profile["disliked_foods"] == [], updated_profile
    stored_profile = db.scalar(select(UserProfileEntity).where(UserProfileEntity.user_id == user.id))
    assert stored_profile.favorite_foods == ""
    assert stored_profile.disliked_foods == ""
    assert service.get_me(db.get(User, user.id))["profile"]["disliked_foods"] == []

    first_log = WeightLog(
        user_id=user.id,
        weight_kg=34,
        log_date=today_vn - timedelta(days=2),
        source="initial_profile",
        is_chart_milestone=True,
    )
    latest_log = WeightLog(
        user_id=user.id,
        weight_kg=34,
        log_date=today_vn - timedelta(days=1),
        source="quick_update",
        is_chart_milestone=False,
    )
    db.add_all([first_log, latest_log])
    db.commit()

    summary = WeightLogService().summary(db, db.get(User, user.id))
    assert_close(summary["current_weight"], 37)
    assert_close(summary["start_weight"], 34)
    assert_close(summary["change_kg"], 3)
    assert_close(summary["gained_kg"], 3)
    assert_close(summary["remaining_kg"], 19)
    assert_close(summary["progress_percent"], 13.6, tolerance=0.1)

    user = db.get(User, user.id)
    service.update_profile(db, user, UserProfileInput(weight_kg=38))
    today_log = db.scalar(
        select(WeightLog).where(WeightLog.user_id == user.id, WeightLog.log_date == today_vn)
    )
    assert today_log is not None
    assert today_log.source == "profile_update"
    assert today_log.log_date.isoformat() == "2026-05-11"
    assert_close(today_log.weight_kg, 38)
    assert WeightLogService.to_payload(today_log)["log_date"].isoformat() == "2026-05-11"
    summary_after_update = WeightLogService().summary(db, db.get(User, user.id))
    assert_close(summary_after_update["current_weight"], 38)
    assert summary_after_update["last_log_date"].isoformat() == "2026-05-11"

    count_before_repository_profile_save = db.scalar(
        select(func.count(WeightLog.id)).where(WeightLog.user_id == user.id)
    )
    stored_profile.weight_kg = 39
    db.commit()
    count_after_repository_profile_save = db.scalar(
        select(func.count(WeightLog.id)).where(WeightLog.user_id == user.id)
    )
    assert count_after_repository_profile_save == count_before_repository_profile_save

    eligible = RecommenderService._build_eligibility_check(
        RecommendationInput(weight=37, height=167, activity="moderate", age=24, sex="female")
    )
    assert eligible["eligible"] is True
    assert eligible["bmi_category"] == "underweight"

    ineligible = RecommenderService._build_eligibility_check(
        RecommendationInput(weight=56, height=167, activity="moderate", age=24, sex="female")
    )
    response = RecommenderService._ineligible_scope_response(ineligible)
    assert response["eligible"] is False
    assert response["reason"] == BMI_NOT_UNDERWEIGHT
    assert response["message"] == BMI_SCOPE_MESSAGE
    assert response["meal_plan"] is None

    print("PASS: sync data smoke checks")
    weight_log_module.now_vn = original_now_vn


if __name__ == "__main__":
    main()
