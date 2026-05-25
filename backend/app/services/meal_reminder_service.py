from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.entities import MealReminderLog, User, UserProfileEntity
from app.services.email_service import is_smtp_configured, send_email


logger = logging.getLogger(__name__)

MEAL_LABELS = {
    "breakfast": "s\u00e1ng",
    "lunch": "tr\u01b0a",
    "dinner": "t\u1ed1i",
}
MEAL_TIME_FIELDS = {
    "breakfast": "breakfast_time",
    "lunch": "lunch_time",
    "dinner": "dinner_time",
}


def _normalize_email(email: str | None) -> str | None:
    text = str(email or "").strip().lower()
    if not text or "@" not in text:
        return None
    local_part, domain = text.split("@", 1)
    if not local_part or not domain:
        return None
    return text


def is_valid_recipient_email(email: str | None) -> bool:
    normalized = _normalize_email(email)
    if not normalized:
        return False
    return not (normalized.endswith(".local") or "@nutrigain.local" in normalized)


def _mask_email(email: str | None) -> str:
    text = str(email or "").strip()
    if "@" not in text:
        return text or "<empty>"
    local_part, domain = text.split("@", 1)
    if not local_part:
        return f"***@{domain}"
    return f"{local_part[0]}***@{domain}"


def _emit_log(message: str, level: str = "info") -> None:
    if level == "warning":
        logger.warning(message)
    else:
        logger.info(message)
    print(message)


def _app_timezone() -> tzinfo:
    try:
        return ZoneInfo(settings.app_timezone or "Asia/Ho_Chi_Minh")
    except ZoneInfoNotFoundError:
        logger.warning("Invalid APP_TIMEZONE=%s; falling back to Asia/Ho_Chi_Minh", settings.app_timezone)
        return timezone(timedelta(hours=7), name="Asia/Ho_Chi_Minh")


class MealReminderService:
    def _reminder_message(self, meal_type: str) -> tuple[str, str, str]:
        meal_label = MEAL_LABELS.get(meal_type, meal_type)
        subject = f"NutriGain nh\u1eafc b\u1ea1n \u0111\u1ebfn gi\u1edd \u0103n {meal_label}"
        text_body = (
            f"Ch\u00e0o b\u1ea1n,\n\n"
            f"\u0110\u00e3 \u0111\u1ebfn gi\u1edd \u0103n {meal_label} r\u1ed3i. H\u00e3y \u0103n nh\u1eb9 nh\u00e0ng v\u00e0 \u0111\u1ec1u \u0111\u1eb7n theo k\u1ebf ho\u1ea1ch h\u00f4m nay nh\u00e9.\n\n"
            f"M\u1ed9t b\u01b0\u1edbc nh\u1ecf m\u1ed7i ng\u00e0y c\u0169ng r\u1ea5t \u0111\u00e1ng ghi nh\u1eadn.\n\n"
            f"NutriGain"
        )
        html_body = (
            "<h2>\u0110\u1ebfn gi\u1edd \u0103n "
            f"{meal_label} r\u1ed3i</h2>"
            "<p>Ch\u00e0o b\u1ea1n,</p>"
            f"<p>\u0110\u00e3 \u0111\u1ebfn gi\u1edd \u0103n {meal_label} r\u1ed3i. "
            "H\u00e3y \u0103n nh\u1eb9 nh\u00e0ng v\u00e0 \u0111\u1ec1u \u0111\u1eb7n theo k\u1ebf ho\u1ea1ch h\u00f4m nay nh\u00e9.</p>"
            "<p>M\u1ed9t b\u01b0\u1edbc nh\u1ecf m\u1ed7i ng\u00e0y c\u0169ng r\u1ea5t \u0111\u00e1ng ghi nh\u1eadn.</p>"
            "<p>NutriGain</p>"
        )
        return subject, text_body, html_body

    @staticmethod
    def _resolve_recipient(user: User, profile: UserProfileEntity | None = None) -> str | None:
        user_email = _normalize_email(getattr(user, "email", None))
        return user_email if is_valid_recipient_email(user_email) else None

    def send_meal_reminder_email(self, email: str, meal_type: str, user_id: int | None = None) -> str:
        if not is_smtp_configured():
            logger.warning("Email reminder skipped: SMTP not configured")
            _emit_log(f"[MEAL REMINDER SKIPPED] reason=smtp_not_configured user_id={user_id}")
            return "skipped"

        recipient = _normalize_email(email)
        if recipient is None:
            _emit_log(f"[MEAL REMINDER SKIPPED] user_id={user_id}, reason=no_user_email")
            return "skipped"
        if not is_valid_recipient_email(recipient):
            _emit_log(f"[MEAL REMINDER SKIPPED] user_id={user_id}, reason=invalid_user_email, email={_mask_email(recipient)}")
            return "skipped"

        _emit_log(f"[MEAL REMINDER EMAIL TO] user_id={user_id}, to={_mask_email(recipient)}, meal_type={meal_type}")
        subject, text_body, html_body = self._reminder_message(meal_type)
        sent = send_email(recipient, subject, html_body, text_body=text_body)
        return "sent" if sent else "failed"

    def _already_logged(self, db: Session, user_id: int, meal_type: str, reminder_date) -> bool:
        existing = db.scalar(
            select(MealReminderLog.id).where(
                MealReminderLog.user_id == user_id,
                MealReminderLog.meal_type == meal_type,
                MealReminderLog.reminder_date == reminder_date,
            )
        )
        return existing is not None

    def _save_log(
        self,
        db: Session,
        user_id: int,
        meal_type: str,
        scheduled_time: str,
        reminder_date,
        sent_at: datetime,
        status: str,
        error_message: str | None = None,
    ) -> None:
        db.add(
            MealReminderLog(
                user_id=user_id,
                meal_type=meal_type,
                scheduled_time=scheduled_time,
                reminder_date=reminder_date,
                sent_at=sent_at.replace(tzinfo=None),
                status=status,
                error_message=(error_message or "")[:255] or None,
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()

    def process_due_reminders(self, db: Session, now: datetime | None = None) -> dict[str, int]:
        tz = _app_timezone()
        local_now = now.astimezone(tz) if now and now.tzinfo else (now or datetime.now(tz))
        current_time = local_now.strftime("%H:%M")
        reminder_date = local_now.date()
        counts = {"checked": 0, "sent": 0, "skipped": 0, "failed": 0}

        _emit_log(f"[MEAL REMINDER CHECK] now={local_now.isoformat(timespec='minutes')}")

        rows = db.execute(
            select(User, UserProfileEntity)
            .join(UserProfileEntity, UserProfileEntity.user_id == User.id)
            .where(UserProfileEntity.meal_reminder_enabled.is_(True), User.is_active.is_(True))
        ).all()

        for user, profile in rows:
            counts["checked"] += 1
            user_role = str(getattr(user, "role", "") or "").upper()
            user_email = _normalize_email(getattr(user, "email", None))
            if user_role in {"ADMIN", "SUPER_ADMIN"} or (user_email and (user_email.endswith(".local") or "@nutrigain.local" in user_email)):
                _emit_log(f"[MEAL REMINDER SKIPPED] user_id={user.id}, reason=admin_or_local_email")
                counts["skipped"] += 1
                continue

            _emit_log(
                "[MEAL REMINDER USER SETTINGS] "
                f"user_id={user.id}, email={_mask_email(getattr(user, 'email', None))}, enabled={bool(profile.meal_reminder_enabled)}, "
                f"breakfast={profile.breakfast_time}, lunch={profile.lunch_time}, dinner={profile.dinner_time}"
            )
            for meal_type, field_name in MEAL_TIME_FIELDS.items():
                scheduled_time = getattr(profile, field_name, None)
                if scheduled_time != current_time:
                    continue

                _emit_log(f"[MEAL REMINDER DUE] user_id={user.id}, meal_type={meal_type}")
                if self._already_logged(db, user.id, meal_type, reminder_date):
                    _emit_log(f"[MEAL REMINDER SKIPPED] reason=duplicate user_id={user.id} meal_type={meal_type}")
                    counts["skipped"] += 1
                    continue

                raw_user_email = _normalize_email(getattr(user, "email", None))
                recipient_email = self._resolve_recipient(user, profile)
                if not recipient_email:
                    self._save_log(
                        db,
                        user.id,
                        meal_type,
                        scheduled_time=current_time,
                        reminder_date=reminder_date,
                        sent_at=local_now,
                        status="skipped",
                        error_message="invalid_user_email" if raw_user_email else "no_user_email",
                    )
                    reason = "invalid_user_email" if raw_user_email else "no_user_email"
                    _emit_log(f"[MEAL REMINDER SKIPPED] user_id={user.id}, reason={reason}, email={_mask_email(raw_user_email)}")
                    counts["skipped"] += 1
                    continue

                try:
                    status = self.send_meal_reminder_email(recipient_email, meal_type, user_id=user.id)
                    self._save_log(
                        db,
                        user.id,
                        meal_type,
                        scheduled_time=scheduled_time,
                        reminder_date=reminder_date,
                        sent_at=local_now,
                        status=status,
                        error_message="smtp_not_configured" if status == "skipped" else None,
                    )
                    if status == "sent":
                        _emit_log(f"[MEAL REMINDER SENT] user_id={user.id}, meal_type={meal_type}")
                    elif status == "failed":
                        _emit_log(f"[MEAL REMINDER FAILED] user_id={user.id}, error=send_email_failed", level="warning")
                    else:
                        _emit_log(f"[MEAL REMINDER SKIPPED] reason=smtp_not_configured user_id={user.id} meal_type={meal_type}")
                    counts[status] = counts.get(status, 0) + 1
                except Exception as exc:
                    _emit_log(f"[MEAL REMINDER FAILED] user_id={user.id}, error={exc}", level="warning")
                    self._save_log(
                        db,
                        user.id,
                        meal_type,
                        scheduled_time=scheduled_time,
                        reminder_date=reminder_date,
                        sent_at=local_now,
                        status="failed",
                        error_message=str(exc),
                    )
                    counts["failed"] += 1

        return counts

    def send_test_email(self, user: User, meal_type: str = "breakfast") -> tuple[bool, str, str | None]:
        meal_key = str(meal_type or "breakfast").strip().lower()
        if meal_key not in MEAL_LABELS:
            meal_key = "breakfast"
        recipient_email = self._resolve_recipient(user, getattr(user, "profile", None))
        if not recipient_email:
            raw_user_email = _normalize_email(getattr(user, "email", None))
            reason = "invalid_user_email" if raw_user_email else "no_user_email"
            _emit_log(f"[MEAL REMINDER SKIPPED] user_id={user.id}, reason={reason}, email={_mask_email(raw_user_email)}")
            if raw_user_email and (raw_user_email.endswith(".local") or "@nutrigain.local" in raw_user_email):
                return False, "Tài khoản admin không dùng nhắc giờ ăn qua email.", None
            return False, "Tài khoản chưa có email thật để nhận nhắc nhở.", None
        if not is_smtp_configured():
            logger.warning("Email reminder skipped: SMTP not configured")
            return False, "SMTP chưa được cấu hình.", None

        subject, text_body, html_body = self._reminder_message(meal_key)
        _emit_log(f"[MEAL REMINDER EMAIL TO] user_id={user.id}, to={_mask_email(recipient_email)}, meal_type={meal_key}")
        sent = send_email(recipient_email, subject, html_body, text_body=text_body)
        if sent:
            _emit_log(f"[MEAL REMINDER SENT] user_id={user.id}, meal_type={meal_key}")
            return True, "Đã gửi email thử.", _mask_email(recipient_email)
        _emit_log(f"[MEAL REMINDER FAILED] user_id={user.id}, error=send_test_email_failed", level="warning")
        return False, "Chưa gửi được email. Vui lòng kiểm tra cấu hình SMTP.", None


_service = MealReminderService()
_stop_event = threading.Event()
_thread: threading.Thread | None = None


def _scheduler_loop(interval_seconds: int = 60) -> None:
    while not _stop_event.is_set():
        try:
            with SessionLocal() as db:
                check_and_send_meal_reminders(db)
        except Exception as exc:
            logger.warning("Meal reminder scheduler tick failed: %s", exc)
        _stop_event.wait(interval_seconds)


def start_meal_reminder_scheduler(interval_seconds: int = 60) -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(
        target=_scheduler_loop,
        kwargs={"interval_seconds": max(60, int(interval_seconds or 60))},
        name="meal-reminder-scheduler",
        daemon=True,
    )
    _thread.start()
    _emit_log("[MEAL REMINDER SCHEDULER STARTED]")


def stop_meal_reminder_scheduler() -> None:
    _stop_event.set()


def check_and_send_meal_reminders(db: Session, now: datetime | None = None) -> dict[str, int]:
    return _service.process_due_reminders(db, now=now)


def send_test_meal_reminder_email(user: User, meal_type: str = "breakfast") -> tuple[bool, str, str | None]:
    return _service.send_test_email(user, meal_type)
