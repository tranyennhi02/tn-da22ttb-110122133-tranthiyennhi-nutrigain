from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings


logger = logging.getLogger(__name__)


def _mask_email(email: str | None) -> str:
    text = str(email or "").strip()
    if "@" not in text:
        return text or "<empty>"
    local_part, domain = text.split("@", 1)
    if not local_part:
        return f"***@{domain}"
    return f"{local_part[0]}***@{domain}"


def _is_local_email(email: str | None) -> bool:
    lowered = str(email or "").strip().lower()
    return lowered.endswith(".local") or "@nutrigain.local" in lowered


def is_smtp_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> bool:
    if not is_smtp_configured():
        logger.warning("Email reminder skipped: SMTP not configured")
        return False

    if not to_email or "@" not in str(to_email):
        logger.warning("[MEAL REMINDER SKIPPED] reason=invalid_email to_email=%s", _mask_email(to_email))
        return False
    if _is_local_email(to_email):
        logger.warning("[MEAL REMINDER SKIPPED] reason=invalid_user_email to_email=%s", _mask_email(to_email))
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from or settings.smtp_user
    message["To"] = to_email

    plain_text = text_body or "NutriGain"
    message.set_content(plain_text)
    message.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port or 587, timeout=15) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
        return True
    except Exception:
        logger.exception("[MEAL REMINDER FAILED] error=send_email_exception")
        return False
