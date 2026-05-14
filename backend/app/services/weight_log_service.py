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

    def upsert_weight_log_from_profile_update(
        self,
        user: User,
        weight_kg: float | None,
        db: Session,
        source: str = "profile_update",
    ) -> dict | None:
        if weight_kg is None:
            return None

        log_date = today_vn()
        print("[PROFILE WEIGHT UPDATE]", {
            "user_id": user.id,
            "email": user.email,
            "payload_weight": weight_kg,
            "today_vn": str(log_date),
        })

        existing = db.scalar(
            select(WeightLog)
            .where(WeightLog.user_id == user.id, WeightLog.log_date == log_date)
        )
        action = "insert"
        recorded_at = now_vn()

        if existing:
            if existing.source == "initial_profile" and source != "initial_profile":
                action = "skip_initial_profile"
                print("[WEIGHT LOG UPSERT FROM PROFILE]", {
                    "user_id": user.id,
                    "log_date": str(log_date),
                    "new_weight": float(weight_kg),
                    "existing_log_id": existing.id,
                    "existing_source": existing.source,
                    "action": action,
                })
                return self.to_payload(existing)

            existing.weight_kg = float(weight_kg)
            existing.updated_at = recorded_at
            existing.source = source
            db.flush()
            db.commit()
            db.refresh(existing)
            action = "update"
            print("[WEIGHT LOG UPSERT FROM PROFILE]", {
                "user_id": user.id,
                "log_date": str(log_date),
                "new_weight": float(weight_kg),
                "existing_log_id": existing.id,
                "existing_source": existing.source,
                "action": action,
            })
            return self.to_payload(existing)

        new_row = WeightLog(
            user_id=user.id,
            weight_kg=float(weight_kg),
            log_date=log_date,
            source=source,
            created_at=recorded_at,
            updated_at=recorded_at,
        )
        db.add(new_row)
        db.flush()
        db.commit()
        db.refresh(new_row)
        print("[WEIGHT LOG UPSERT FROM PROFILE]", {
            "user_id": user.id,
            "log_date": str(log_date),
            "new_weight": float(weight_kg),
            "existing_log_id": None,
            "existing_source": None,
            "action": action,
        })
        return self.to_payload(new_row)

    @staticmethod
    def _raw_logs_debug_payload(raw_logs: list[WeightLog]) -> list[dict]:
        return [
            {
                "id": log.id,
                "user_id": log.user_id,
                "weight_kg": log.weight_kg,
                "log_date": str(log.log_date),
                "source": log.source,
                "created_at": str(log.created_at),
                "updated_at": str(log.updated_at),
            }
            for log in raw_logs
        ]

    @staticmethod
    def _milestone_points(
        all_logs: list[WeightLog],
        today: date,
        profile_weight: float | None = None,
    ) -> tuple[list[dict], date | None]:
        if not all_logs:
            return [], None

        all_logs_sorted = list(all_logs)
        all_logs_sorted.sort(key=lambda l: (l.log_date, getattr(l, "created_at", None) or datetime.min, l.id))
        start_log = all_logs_sorted[0]
        start_date = start_log.log_date
        milestone_points: list[dict] = []

        milestone_date = start_date
        while milestone_date <= today:
            matching_logs = [log for log in all_logs if log.log_date == milestone_date]
            if matching_logs:
                # Sort matching_logs descending: newest first
                matching_logs.sort(
                    key=lambda l: (
                        getattr(l, "updated_at", None) or getattr(l, "created_at", None) or datetime.min,
                        getattr(l, "id", 0)
                    ),
                    reverse=True
                )
                selected_log = matching_logs[0]
                milestone_points.append(
                    {
                        "date": milestone_date.isoformat(),
                        "log_date": milestone_date,
                        "weight_kg": float(selected_log.weight_kg),
                        "label": "initial" if milestone_date == start_date else "milestone",
                        "is_milestone": True,
                        "source": getattr(selected_log, "source", None),
                        "log_id": getattr(selected_log, "id", None),
                        "source_log_date": selected_log.log_date,
                        "note": getattr(selected_log, "note", None),
                    }
                )
            milestone_date += timedelta(days=3)

        print("[MILESTONE POINTS FINAL]", milestone_points)
        next_milestone_date = milestone_date
        return milestone_points, next_milestone_date

    def sync_profile_weight(
        self,
        db: Session,
        user: User,
        weight_kg: float | None,
    ) -> None:
        try:
            self.upsert_weight_log_from_profile_update(user, weight_kg, db, source="profile_update")
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
                if existing.source == "initial_profile" and source != "initial_profile":
                    # Never overwrite the initial snapshot; keep chart history stable and only move the profile forward.
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
        print("[WEIGHT CURRENT USER]", {
            "endpoint": "/weight-logs",
            "user_id": user.id,
            "email": user.email,
        })

        if mode == "milestones":
            print("[WEIGHT RAW LOGS USED]", self._raw_logs_debug_payload(all_logs))
            milestones, _ = self._milestone_points(all_logs, today, profile_weight=None)
            print("[MILESTONE POINTS FINAL]", milestones)

            if range_days is not None:
                cutoff = today - timedelta(days=max(range_days, 0))
                milestones = [m for m in milestones if m["date"] >= cutoff.isoformat()]
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
        print("[WEIGHT CURRENT USER]", {
            "endpoint": "/weight-logs/summary",
            "user_id": user.id,
            "email": user.email,
        })
        print("[WEIGHT RAW LOGS USED]", self._raw_logs_debug_payload(rows))

        rows_sorted = list(rows)
        rows_sorted.sort(key=lambda l: (l.log_date, getattr(l, "created_at", None) or datetime.min, l.id))
        start_log = rows_sorted[0] if rows_sorted else None
        latest_log = rows[-1] if rows else None

        print("[WEIGHT START LOG DEBUG]", {
            "user_id": user.id,
            "email": user.email,
            "start_log_id": start_log.id if start_log else None,
            "start_log_date": str(start_log.log_date) if start_log else None,
            "start_log_weight": start_log.weight_kg if start_log else None,
            "all_logs": self._raw_logs_debug_payload(rows_sorted),
        })

        profile_weight = _profile_weight(profile)
        latest_log_weight = float(latest_log.weight_kg) if latest_log else None
        target_weight = _profile_target_weight(profile)

        start_weight = float(start_log.weight_kg) if start_log else None
        start_date = start_log.log_date if start_log else None

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
        milestone_points, next_milestone_date = self._milestone_points(rows, today, profile_weight=profile_weight)
        last_log_date = latest_log.log_date if latest_log else None

        latest_milestone_date = next_milestone_date - timedelta(days=3) if start_log and next_milestone_date else today
        days_since_latest_milestone = (today - latest_milestone_date).days if start_log else 0
        should_checkin = days_since_latest_milestone >= 3

        print("[MILESTONE POINTS FINAL]", {
            "user_id": user.id,
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
            "latest_milestone_date": latest_milestone_date,
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
