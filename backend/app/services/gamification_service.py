from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.entities import (
    MealConsumptionLog,
    MealPlan,
    WeightLog,
    UserAchievement,
    UserDailyActivity,
    UserChallenge,
)


class GamificationService:
    VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

    def _today_vn(self) -> date:
        return datetime.now(self.VN_TZ).date()

    def _completed_main_meals(self, db: Session, user_id: int, target_date: date) -> bool:
        # consider breakfast, lunch, dinner present if there is at least one MealConsumptionLog per meal_type
        q = db.query(func.count(func.distinct(MealConsumptionLog.meal_type))).filter(
            MealConsumptionLog.user_id == user_id,
            func.date(MealConsumptionLog.consumed_at) == target_date,
            MealConsumptionLog.meal_type.in_(["breakfast", "lunch", "dinner"]),
        )
        cnt = q.scalar() or 0
        return cnt >= 3

    def get_summary(self, db: Session, user) -> dict:
        today = self._today_vn()
        # decide reference date: if today completed then include today, else look at yesterday
        include_today = self._completed_main_meals(db, user.id, today)
        ref_date = today if include_today else (today - timedelta(days=1))

        # compute consecutive days of completed_main_meals backwards from ref_date
        streak = 0
        cursor = ref_date
        while True:
            if self._completed_main_meals(db, user.id, cursor):
                streak += 1
                cursor = cursor - timedelta(days=1)
            else:
                break

        # Auto-recalculate achievements every time summary is fetched
        # so badges unlock as soon as the user meets the criteria
        try:
            self.recalculate(db, user)
        except Exception:
            pass

        # achievements
        achievements = []
        rows = db.query(UserAchievement).filter(UserAchievement.user_id == user.id).order_by(UserAchievement.unlocked_at.desc()).limit(10).all()
        for r in rows:
            achievements.append({
                "key": r.achievement_key,
                "title": r.title,
                "description": r.description,
                "unlocked_at": r.unlocked_at.isoformat() if r.unlocked_at else None,
            })

        # today challenge generation (simple rules)
        # check meals today
        meal_count_today = db.query(func.count()).filter(
            MealConsumptionLog.user_id == user.id,
            func.date(MealConsumptionLog.consumed_at) == today,
        ).scalar() or 0
        has_weight_log_today = db.query(func.count()).filter(
            WeightLog.user_id == user.id,
            WeightLog.log_date == today,
        ).scalar() or 0

        # pick challenge
        if include_today:
            today_challenge = {
                "key": "first_complete_day",
                "title": "Ăn đều hôm nay",
                "description": "Bạn đã hoàn thành đủ bữa sáng, trưa và tối hôm nay.",
                "status": "completed",
            }
        elif meal_count_today > 0:
            today_challenge = {
                "key": "first_complete_day",
                "title": "Ăn đều hôm nay",
                "description": "Hoàn thành đủ bữa sáng, trưa và tối hôm nay.",
                "status": "in_progress",
            }
        else:
            today_challenge = {
                "key": "mark_one_meal",
                "title": "Đánh dấu một bữa đã ăn",
                "description": "Chỉ cần bắt đầu bằng một bữa bạn đã hoàn thành.",
                "status": "not_started",
            }
        if meal_count_today > 0 and not include_today and not has_weight_log_today:
            today_challenge = {
                "key": "update_today_weight",
                "title": "Cập nhật cân nặng hôm nay",
                "description": "Ghi lại cân nặng giúp biểu đồ theo dõi chính xác hơn.",
                "status": "not_started",
            }
        elif meal_count_today > 0 and not include_today:
            today_challenge = {
                "key": "small_step_today",
                "title": "Một bước nhỏ hôm nay",
                "description": "Chọn một việc nhỏ bạn muốn làm để chăm sóc bản thân.",
                "status": "not_started",
            }

        # encouragement messages (choose gently)
        encouragements = [
            "Hôm nay chỉ cần tiến thêm một bước nhỏ.",
            "Ăn đều hơn một chút cũng là tiến bộ.",
            "Bạn không cần hoàn hảo, chỉ cần đều hơn hôm qua.",
            "Nếu hôm nay chưa đủ, ngày mai mình thử lại nhẹ nhàng.",
            "Tăng cân lành mạnh cần thời gian, bạn đang đi đúng hướng.",
        ]

        import random

        encouragement = random.choice(encouragements)

        return {
            "streak": {"current": streak, "label": "Chuỗi ăn đều", "message": streak > 0 and f"Bạn đã ăn đều {streak} ngày liên tiếp." or "Bắt đầu bằng một ngày ăn đều hôm nay nhé."},
            "achievements": achievements,
            "today_challenge": today_challenge,
            "encouragement": encouragement,
        }

    def complete_challenge(self, db: Session, user, challenge_key: str) -> dict:
        today = self._today_vn()
        # upsert UserChallenge for today
        row = db.query(UserChallenge).filter(
            UserChallenge.user_id == user.id,
            UserChallenge.challenge_key == challenge_key,
            UserChallenge.challenge_date == today,
        ).first()
        if row and row.status == "completed":
            return {"success": True, "message": "Bạn đã hoàn thành việc này hôm nay.", "summary": self.get_summary(db, user)}
        if not row:
            row = UserChallenge(
                user_id=user.id,
                challenge_key=challenge_key,
                challenge_date=today,
                status="completed",
                completed_at=datetime.utcnow(),
            )
            db.add(row)
        else:
            row.status = "completed"
            row.completed_at = datetime.utcnow()
        # update or create daily activity
        da = db.query(UserDailyActivity).filter(UserDailyActivity.user_id == user.id, UserDailyActivity.activity_date == today).first()
        if not da:
            da = UserDailyActivity(user_id=user.id, activity_date=today, meals_completed_count=0, completed_main_meals=False, updated_weight=False, completed_lesson=False, completed_challenge_key=challenge_key)
            db.add(da)
        else:
            da.completed_challenge_key = challenge_key
        db.commit()

        # recalculate achievements for user
        # The following line was incorrectly marked for removal
        # It is important to keep this line for committing changes to the database
        
        try:
            self.recalculate(db, user)
        except Exception:
            db.rollback()

        # return updated summary
        summary = self.get_summary(db, user)
        return {"success": True, "message": "Bạn đã hoàn thành một việc nhỏ hôm nay. Rất đáng ghi nhận.", "summary": summary}

    def recalculate(self, db: Session, user=None):
        # if user passed, only recalc for that user; otherwise for all users (expensive)
        users = [user] if user is not None else db.query(func.distinct(MealConsumptionLog.user_id)).all()
        target_users = []
        if user is not None:
            target_users = [user]
        else:
            # convert tuples
            target_users = [db.query(MealConsumptionLog).filter(MealConsumptionLog.user_id == u[0]).first() for u in users]
            target_users = [t for t in target_users if t is not None]

        for u in target_users:
            uid = u.id if hasattr(u, "id") else getattr(u, "user_id", None)
            if uid is None:
                continue
            # achievements checks
            # first_meal_plan
            has_meal_plan = db.query(func.count()).filter(MealPlan.user_id == uid).scalar() or 0
            if has_meal_plan:
                if not db.query(UserAchievement).filter(UserAchievement.user_id == uid, UserAchievement.achievement_key == "first_meal_plan").first():
                    ach = UserAchievement(user_id=uid, achievement_key="first_meal_plan", title="Bắt đầu nhẹ nhàng", description="Bạn đã tạo thực đơn đầu tiên.")
                    db.add(ach)
            # first_weight_log
            has_weight = db.query(func.count()).filter(WeightLog.user_id == uid).scalar() or 0
            if has_weight:
                if not db.query(UserAchievement).filter(UserAchievement.user_id == uid, UserAchievement.achievement_key == "first_weight_log").first():
                    ach = UserAchievement(user_id=uid, achievement_key="first_weight_log", title="Theo dõi cân nặng", description="Bạn đã ghi nhận cân nặng đầu tiên.")
                    db.add(ach)
            # first_complete_day
            # check any day with completed_main_meals
            sub = db.query(func.count(func.distinct(func.date(MealConsumptionLog.consumed_at)))).filter(MealConsumptionLog.user_id == uid).scalar() or 0
            if sub:
                # naive: if there is at least one day with breakfast/lunch/dinner
                has_complete_day = False
                days = db.query(func.date(MealConsumptionLog.consumed_at)).filter(MealConsumptionLog.user_id == uid).distinct().all()
                for d in days:
                    dt = d[0]
                    if self._completed_main_meals(db, uid, dt):
                        has_complete_day = True
                        break
                if has_complete_day:
                    if not db.query(UserAchievement).filter(UserAchievement.user_id == uid, UserAchievement.achievement_key == "first_complete_day").first():
                        ach = UserAchievement(user_id=uid, achievement_key="first_complete_day", title="Ăn đều hôm nay", description="Bạn đã duy trì đủ các bữa chính trong một ngày.")
                        db.add(ach)
            # three_active_days
            active_days = db.query(func.count(func.distinct(func.date(MealConsumptionLog.consumed_at)))).filter(MealConsumptionLog.user_id == uid).scalar() or 0
            if active_days >= 3:
                if not db.query(UserAchievement).filter(UserAchievement.user_id == uid, UserAchievement.achievement_key == "three_active_days").first():
                    ach = UserAchievement(user_id=uid, achievement_key="three_active_days", title="Bạn đồng hành 3 ngày", description="Bạn đã quay lại chăm sóc bản thân trong 3 ngày.")
                    db.add(ach)
            # three_balanced_days_in_week
            today = self._today_vn()
            week_start = today - timedelta(days=6)
            balanced_count = 0
            for i in range(7):
                d = week_start + timedelta(days=i)
                if self._completed_main_meals(db, uid, d):
                    balanced_count += 1
            if balanced_count >= 3:
                if not db.query(UserAchievement).filter(UserAchievement.user_id == uid, UserAchievement.achievement_key == "three_balanced_days_in_week").first():
                    ach = UserAchievement(user_id=uid, achievement_key="three_balanced_days_in_week", title="Duy trì nhẹ nhàng", description="Bạn đã có 3 ngày ăn đều trong tuần này.")
                    db.add(ach)

            # discipline_eater — ăn đủ 3 bữa liên tục 7 ngày (streak >= 7)
            streak_count = 0
            cursor = today
            while True:
                if self._completed_main_meals(db, uid, cursor):
                    streak_count += 1
                    cursor = cursor - timedelta(days=1)
                else:
                    break
            if streak_count >= 7:
                if not db.query(UserAchievement).filter(UserAchievement.user_id == uid, UserAchievement.achievement_key == "discipline_eater").first():
                    ach = UserAchievement(user_id=uid, achievement_key="discipline_eater", title="Kỷ luật ăn uống", description="Bạn đã duy trì ăn đủ 3 bữa liên tục 7 ngày.")
                    db.add(ach)

            # diverse_menu — đã đánh dấu ăn ít nhất 5 ngày khác nhau
            if active_days >= 5:
                if not db.query(UserAchievement).filter(UserAchievement.user_id == uid, UserAchievement.achievement_key == "diverse_menu").first():
                    ach = UserAchievement(user_id=uid, achievement_key="diverse_menu", title="Thực đơn đa dạng", description="Bạn đã quay lại ghi nhận bữa ăn trong 5 ngày.")
                    db.add(ach)

            # perfect_calories — đã có ít nhất 1 ngày ăn đủ cả 3 bữa chính (dùng lại first_complete_day điều kiện tương tự)
            # trao khi đã ăn đủ 3 bữa ít nhất 3 ngày khác nhau
            complete_day_count = 0
            all_days = db.query(func.date(MealConsumptionLog.consumed_at)).filter(MealConsumptionLog.user_id == uid).distinct().all()
            for d in all_days:
                if self._completed_main_meals(db, uid, d[0]):
                    complete_day_count += 1
            if complete_day_count >= 3:
                if not db.query(UserAchievement).filter(UserAchievement.user_id == uid, UserAchievement.achievement_key == "perfect_calories").first():
                    ach = UserAchievement(user_id=uid, achievement_key="perfect_calories", title="Calories hoàn hảo", description="Bạn đã hoàn thành đủ 3 bữa chính trong 3 ngày.")
                    db.add(ach)

        db.commit()
 