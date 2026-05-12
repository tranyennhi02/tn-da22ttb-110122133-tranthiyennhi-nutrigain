from __future__ import annotations

from datetime import date, timedelta, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.entities import User, UserProfileEntity, WeightLog
from app.views.schemas import WeightLogCreate


from zoneinfo import ZoneInfo

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

def now_vn():
    return datetime.now(VN_TZ)

def today_vn():
    return now_vn().date()


def _as_vn_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=VN_TZ)
    return value.astimezone(VN_TZ)

TREND_MESSAGES = {
    "increasing": "Bạn đang tăng cân tốt. Hãy tiếp tục duy trì kế hoạch ăn uống.",
    "stable": "Cân nặng chưa thay đổi trong lần cập nhật gần nhất. Hãy kiểm tra lại lượng kcal đã ăn.",
    "decreasing": "Cân nặng đang giảm nhẹ. Có thể bạn cần tăng kcal hoặc theo dõi bữa ăn sát hơn.",
    "not_enough_data": "Hãy cập nhật cân nặng mỗi 3 ngày để NutriGain theo dõi xu hướng chính xác hơn.",
}
INITIAL_WEIGHT_MESSAGE = "Đã ghi nhận cân nặng ban đầu. Hãy cập nhật lại sau 3 ngày để theo dõi xu hướng tăng cân."
PROFILE_INITIAL_NOTE = "Cân nặng khởi tạo từ hồ sơ"
PROFILE_UPDATE_NOTE = "Cân nặng cập nhật từ hồ sơ"


def _round_optional(value: float | None, digits: int = 1) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


class WeightLogService:
    @staticmethod
    def to_payload(row: WeightLog) -> dict:
        created_at = _as_vn_datetime(row.created_at)
        updated_at = _as_vn_datetime(getattr(row, "updated_at", None))

        log_date = row.log_date
        if not log_date and created_at:
            log_date = created_at.date()

        return {
            "id": row.id,
            "user_id": row.user_id,
            "weight_kg": float(row.weight_kg),
            "log_date": log_date,
            "note": row.note,
            "source": getattr(row, "source", None),
            "is_chart_milestone": bool(getattr(row, "is_chart_milestone", False)),
            "created_at": created_at,
            "updated_at": updated_at,
        }

    def save_log(self, db: Session, user: User, payload: WeightLogCreate) -> dict:
        # Quick update route: treat as user-initiated quick_update
        return self.upsert_weight_log(db, user.id, float(payload.weight_kg), payload.log_date, payload.note, source="quick_update")

    def sync_profile_weight(
        self,
        db: Session,
        user: User,
        weight_kg: float | None,
    ) -> None:
        if weight_kg is None: return
        try:
            first_log = db.scalar(
                select(WeightLog)
                .where(WeightLog.user_id == user.id)
                .order_by(WeightLog.log_date.asc(), WeightLog.id.asc())
            )
            source = "profile_update" if first_log else "initial_profile"
            note = PROFILE_UPDATE_NOTE if first_log else PROFILE_INITIAL_NOTE
            
            self.upsert_weight_log(
                db,
                user.id,
                weight_kg,
                today_vn(),
                note,
                source=source,
            )
        except Exception:
            db.rollback()

    def upsert_weight_log(self, db: Session, user_id: int, weight_kg: float | None, log_date: date | None = None, note: str | None = None, source: str = "profile_form") -> dict | None:
        if weight_kg is None:
            return None
        try:
            weight_value = float(weight_kg)
        except (TypeError, ValueError):
            return None
        if weight_value <= 0:
            return None

        target_date = log_date or today_vn()
        note = note.strip() if isinstance(note, str) and note.strip() else None

        existing = db.scalar(
            select(WeightLog).where(WeightLog.user_id == user_id, WeightLog.log_date == target_date)
        )
        try:
            recorded_at = now_vn()
            recorded_date = target_date

            print("[WEIGHT LOG DATE DEBUG]", {
                "now_vn": now_vn().isoformat(),
                "today_vn": str(today_vn()),
                "recorded_at": recorded_at,
                "recorded_date": recorded_date,
                "source": source,
                "weight_kg": weight_value,
            })

            if existing:
                if existing.source == "initial_profile" and source != "initial_profile" and source != "profile_update":
                    # Cannot overwrite initial profile weight on the same day! But we MUST update profile.weight_kg
                    profile = db.scalar(select(UserProfileEntity).where(UserProfileEntity.user_id == user_id))
                    if profile:
                        if abs(float(profile.weight_kg or 0) - weight_value) >= 0.05:
                            print(f"[PROFILE WRITE SOURCE] weight_log_service.py:upsert_weight_log values={{'weight_kg': {weight_value}}}")
                            profile.weight_kg = weight_value
                    db.commit()
                    return self.to_payload(existing)
                
                # Normal overwrite
                existing.weight_kg = float(weight_value)
                existing.log_date = recorded_date
                existing.source = source
                if note and not existing.note:
                    existing.note = note
                existing.created_at = recorded_at
                existing.updated_at = recorded_at
                db.flush()

                profile = db.scalar(select(UserProfileEntity).where(UserProfileEntity.user_id == user_id))
                if profile:
                    print(f"[PROFILE WRITE SOURCE] weight_log_service.py:upsert_weight_log values={{'weight_kg': {weight_value}}}")
                    profile.weight_kg = weight_value
                db.commit()
                db.refresh(existing)
                return self.to_payload(existing)

            new_row = WeightLog(
                user_id=user_id,
                weight_kg=float(weight_value),
                log_date=target_date,
                note=note,
                source=source,
                is_chart_milestone=False,
                created_at=recorded_at,
                updated_at=recorded_at
            )
            db.add(new_row)
            db.flush()

            profile = db.scalar(select(UserProfileEntity).where(UserProfileEntity.user_id == user_id))
            if profile is None:
                profile = UserProfileEntity(user_id=user_id)
                db.add(profile)
            print(f"[PROFILE WRITE SOURCE] weight_log_service.py:upsert_weight_log values={{'weight_kg': {weight_value}}}")
            profile.weight_kg = float(weight_value)

            db.commit()
            db.refresh(new_row)
            return self.to_payload(new_row)
        except SQLAlchemyError:
            db.rollback()
            return None

    def list_logs(self, db: Session, user: User, range_days: int | None = 30, mode: str = "milestones") -> list[dict]:
        query = select(WeightLog).where(WeightLog.user_id == user.id).order_by(WeightLog.log_date.asc())
        all_logs = list(db.scalars(query))
        if not all_logs:
            return []

        today = today_vn()

        if mode == "milestones":
            start_log = next((l for l in all_logs if l.source == "initial_profile"), all_logs[0])
            start_date = start_log.log_date
            
            milestones = []
            current_mc_date = start_date
            
            profile = user.profile or db.scalar(
                select(UserProfileEntity).where(UserProfileEntity.user_id == user.id)
            )
            profile_weight = float(profile.weight_kg) if profile and profile.weight_kg is not None else None

            def find_log_for_date(target_d):
                valid = [l for l in all_logs if l.log_date <= target_d]
                if valid:
                    return valid[-1]
                return start_log

            while current_mc_date <= today:
                log = find_log_for_date(current_mc_date)
                m_payload = self.to_payload(log)
                m_payload["log_date"] = current_mc_date
                if current_mc_date == today and profile_weight is not None:
                    m_payload["weight_kg"] = float(profile_weight)
                milestones.append(m_payload)
                current_mc_date += timedelta(days=3)

            if milestones and profile_weight is not None:
                milestones[-1]["weight_kg"] = float(profile_weight)

            if range_days is not None:
                cutoff = today - timedelta(days=max(range_days, 0))
                milestones = [m for m in milestones if m["log_date"] >= cutoff]
            return milestones

        if range_days is not None:
            cutoff = today - timedelta(days=max(range_days, 0))
            all_logs = [l for l in all_logs if l.log_date >= cutoff]
        return [self.to_payload(row) for row in all_logs]

    def summary(self, db: Session, user: User) -> dict:
        print("### RUNNING NEW WEIGHT SUMMARY CODE v999 ###")
        rows = list(
            db.scalars(
                select(WeightLog)
                .where(WeightLog.user_id == user.id)
                .order_by(WeightLog.log_date.asc())
            )
        )
        profile = user.profile or db.scalar(
            select(UserProfileEntity).where(UserProfileEntity.user_id == user.id)
        )

        start_log = next((l for l in rows if l.source == "initial_profile"), rows[0] if rows else None)
        latest_log = rows[-1] if rows else None

        profile_weight = _profile_weight(profile)
        latest_log_weight = float(latest_log.weight_kg) if latest_log else None
        target_weight = _profile_target_weight(profile)

        start_weight = float(start_log.weight_kg) if start_log else profile_weight
        start_date = start_log.log_date if start_log else today_vn()

        current_weight = profile_weight if profile_weight is not None else latest_log_weight
        if current_weight is None and start_weight is not None:
             current_weight = start_weight
             
        if current_weight is not None and start_weight is not None:
            change_kg = current_weight - start_weight
            gained_kg = change_kg
        else:
            change_kg = None
            gained_kg = None

        remaining_kg = None
        if target_weight is not None and current_weight is not None:
            remaining_kg = max(target_weight - current_weight, 0.0)

        progress_percent = 0.0
        if target_weight is not None and current_weight is not None and start_weight is not None:
            if target_weight <= start_weight:
                progress_percent = 0.0
            else:
                raw_progress = ((current_weight - start_weight) / (target_weight - start_weight)) * 100
                progress_percent = min(100.0, max(0.0, raw_progress))

        trend = "not_enough_data"
        if gained_kg is not None:
            if gained_kg > 0: trend = "increasing"
            elif gained_kg < 0: trend = "decreasing"
            else: trend = "stable"

        today = today_vn()
        
        milestone_points = []
        next_milestone_date = start_date + timedelta(days=3) if start_log else today + timedelta(days=3)
        last_log_date = latest_log.log_date if latest_log else None
        
        if start_log:
            current_mc_date = start_date
            def find_log_for_date(target_d):
                valid = [l for l in rows if l.log_date <= target_d]
                return valid[-1] if valid else start_log

            while current_mc_date <= today:
                log = find_log_for_date(current_mc_date)
                w = float(log.weight_kg)
                if current_mc_date == today and profile_weight is not None:
                    w = float(profile_weight)
                milestone_points.append({
                    "date": current_mc_date.isoformat(),
                    "weight_kg": w,
                    "type": "initial" if current_mc_date == start_date else "milestone"
                })
                current_mc_date += timedelta(days=3)
            next_milestone_date = current_mc_date
            
            if milestone_points and profile_weight is not None:
                milestone_points[-1]["weight_kg"] = float(profile_weight)

        days_since_latest_milestone = (today - (next_milestone_date - timedelta(days=3))).days if start_log else 0
        should_checkin = days_since_latest_milestone >= 3

        print("[MILESTONE POINTS FINAL]", {
            "profile_weight": profile.weight_kg if profile else None,
            "today": today,
            "milestone_points": milestone_points,
        })

        print("[WEIGHT SUMMARY FINAL]", {
            "start_date": start_date,
            "start_weight": start_weight,
            "current_weight": current_weight,
            "target_weight": target_weight,
            "gained_kg": gained_kg,
            "change_kg": change_kg,
            "remaining_kg": remaining_kg,
            "progress_percent": progress_percent,
            "trend": trend,
            "start_log_id": getattr(start_log, "id", None) if start_log else None,
            "start_log_source": getattr(start_log, "source", None) if start_log else None,
        })

        return {
            "start_date": start_date,
            "current_weight": _round_optional(current_weight),
            "start_weight": _round_optional(start_weight),
            "target_weight": _round_optional(target_weight),
            "change_kg": _round_optional(change_kg),
            "gained_kg": _round_optional(gained_kg),
            "remaining_kg": _round_optional(remaining_kg),
            "progress_percent": round(progress_percent, 2),
            "trend": trend,
            "last_log_date": last_log_date,
            "latest_milestone_date": next_milestone_date - timedelta(days=3) if start_log else today,
            "next_checkin_date": next_milestone_date,
            "next_milestone_date": next_milestone_date,
            "milestone_points": milestone_points,
            "days_since_latest_milestone": days_since_latest_milestone,
            "should_checkin": should_checkin,
            "message": INITIAL_WEIGHT_MESSAGE if len(rows) <= 1 else TREND_MESSAGES.get(trend, "not_enough_data"),
        }


def _profile_weight(profile: UserProfileEntity | None) -> float | None:
    return float(profile.weight_kg) if profile is not None and profile.weight_kg is not None else None


def _profile_initial_weight(profile: UserProfileEntity | None) -> float | None:
    value = getattr(profile, "initial_weight_kg", None) if profile is not None else None
    return float(value) if value is not None else None


def _profile_target_weight(profile: UserProfileEntity | None) -> float | None:
    if profile is None or profile.target_weight_kg is None:
        return None
    return float(profile.target_weight_kg)
