from __future__ import annotations

import os
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


def _is_dev_mode() -> bool:
    frontend_url = str(settings.frontend_url or "").lower()
    env = str(settings.app_env or os.getenv("ENVIRONMENT", "") or os.getenv("ENV", "")).lower()
    return "localhost" in frontend_url or "127.0.0.1" in frontend_url or env in {"development", "dev", "local"} or str(os.getenv("DEBUG", "")).lower() == "true"


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


def send_verification_code_email(to_email: str, code: str) -> bool:
    logger.info("[EMAIL VERIFICATION SEND START] to_email=%s", _mask_email(to_email))
    
    # Log SMTP configuration status (safely, without passwords)
    logger.info(
        "[SMTP CONFIG CHECK] host_set=%s port=%s user_set=%s password_set=%s from_email=%s use_tls=%s",
        bool(settings.smtp_host),
        settings.smtp_port,
        bool(settings.smtp_user),
        bool(settings.smtp_password),
        settings.smtp_from or settings.smtp_user,
        settings.smtp_use_tls,
    )
    
    if not to_email or "@" not in str(to_email):
        logger.warning("[EMAIL VERIFICATION SEND FAILED] reason=invalid_email to_email=%s", _mask_email(to_email))
        return False

    if not is_smtp_configured():
        if _is_dev_mode():
            logger.warning("[EMAIL DEV MODE] Verification code for %s: %s", _mask_email(to_email), code)
            logger.warning("[EMAIL VERIFICATION SEND FAILED] reason=smtp_not_configured_dev_mode")
        else:
            logger.warning("[EMAIL VERIFICATION SEND FAILED] reason=smtp_not_configured to_email=%s", _mask_email(to_email))
        return False

    message = EmailMessage()
    message["Subject"] = "Xác thực email NutriGain"
    message["From"] = settings.smtp_from or settings.smtp_user
    message["To"] = to_email
    message.set_content(
        "Bạn vừa đăng ký NutriGain.\n\n"
        f"Mã xác thực của bạn là: {code}\n\n"
        "Mã này sẽ hết hạn sau 10 phút. Nếu bạn không yêu cầu, hãy bỏ qua email này."
    )
    message.add_alternative(
        f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #0f172a;">
          <h2>Xác thực email NutriGain</h2>
          <p>Bạn vừa đăng ký tài khoản. Dùng mã sau để hoàn tất xác thực email:</p>
          <div style="font-size: 28px; font-weight: 700; letter-spacing: 8px; margin: 16px 0;">{code}</div>
          <p>Mã này sẽ hết hạn sau 10 phút.</p>
        </div>
        """,
        subtype="html",
    )

    try:
        logger.info("[SMTP SEND START] host=%s port=%s", settings.smtp_host, settings.smtp_port)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port or 587, timeout=15) as smtp:
            if settings.smtp_use_tls:
                logger.info("[SMTP TLS START]")
                smtp.starttls()
                logger.info("[SMTP TLS SUCCESS]")
            
            logger.info("[SMTP LOGIN START] user=%s", _mask_email(settings.smtp_user))
            smtp.login(settings.smtp_user, settings.smtp_password)
            logger.info("[SMTP LOGIN SUCCESS]")
            
            logger.info("[SMTP SEND MESSAGE START]")
            smtp.send_message(message)
            logger.info("[SMTP SEND MESSAGE SUCCESS]")
        
        logger.info("[EMAIL VERIFICATION SEND SUCCESS] to_email=%s", _mask_email(to_email))
        return True
    except Exception:
        logger.exception("[EMAIL VERIFICATION SEND FAILED] error=send_verification_email_exception to_email=%s", _mask_email(to_email))
        return False
