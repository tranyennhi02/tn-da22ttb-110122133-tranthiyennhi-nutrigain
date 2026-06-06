from __future__ import annotations

import logging
import re

from app.core.config import settings


logger = logging.getLogger(__name__)


def is_twilio_configured() -> bool:
    """Return True only when all three Twilio credentials are set."""
    return bool(settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_phone_number)


def _normalize_phone(phone: str | None) -> str | None:
    """Normalise a phone number to E.164 format (+84xxxxxxxxx for Vietnam).

    Accepts:
      - International format already with '+'  (+84912345678)
      - Local Vietnamese format starting with 0 (0912345678 → +84912345678)
      - Digits-only strings
    Returns None when the number looks invalid.
    """
    if not phone:
        return None
    # Strip whitespace and common separators
    digits_only = re.sub(r"[\s\-\.\(\)]", "", str(phone).strip())
    if not digits_only:
        return None
    if digits_only.startswith("+"):
        e164 = digits_only
    elif digits_only.startswith("84"):
        e164 = "+" + digits_only
    elif digits_only.startswith("0") and len(digits_only) == 10:
        # Vietnamese local format: replace leading 0 with country code
        e164 = "+84" + digits_only[1:]
    else:
        # Assume already missing the leading 0, try to infer
        e164 = "+" + digits_only

    # Basic length sanity check (E.164 is 8–15 digits after '+')
    clean = e164.lstrip("+")
    if not clean.isdigit() or not (7 <= len(clean) <= 15):
        return None
    return e164


def _mask_phone(phone: str | None) -> str:
    """Return a partially masked phone number for safe logging."""
    text = str(phone or "").strip()
    if len(text) < 4:
        return "***"
    return text[:3] + "***" + text[-2:]


def send_sms(to_phone: str, body: str) -> bool:
    """Send a plain-text SMS via Twilio.

    Returns True on success, False otherwise.
    Skips sending gracefully when Twilio is not configured.
    """
    if not is_twilio_configured():
        logger.warning("[SMS SKIPPED] reason=twilio_not_configured")
        return False

    recipient = _normalize_phone(to_phone)
    if not recipient:
        logger.warning("[SMS SKIPPED] reason=invalid_phone to_phone=%s", _mask_phone(to_phone))
        return False

    try:
        # Import here so the rest of the app works even without twilio installed
        from twilio.rest import Client  # type: ignore[import-untyped]

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        message = client.messages.create(
            body=body,
            from_=settings.twilio_phone_number,
            to=recipient,
        )
        logger.info("[SMS SENT] to=%s sid=%s", _mask_phone(recipient), message.sid)
        return True
    except ImportError:
        logger.error("[SMS FAILED] reason=twilio_not_installed — run: pip install twilio")
        return False
    except Exception:
        logger.exception("[SMS FAILED] to=%s", _mask_phone(recipient))
        return False
