from __future__ import annotations

import logging
import re

import requests

from app.core.config import settings


logger = logging.getLogger(__name__)


def is_twilio_configured() -> bool:
    """Return True only when eSMS.vn API credentials are set."""
    from app.core.config import settings as config_settings
    api_key = config_settings.esms_api_key
    secret_key = config_settings.esms_secret_key
    is_configured = bool(api_key and secret_key)
    
    print(f"[DEBUG is_twilio_configured] api_key={repr(api_key)[:20]}... secret_key={repr(secret_key)[:20]}... result={is_configured}")
    
    logger.info(
        "[ESMS CONFIG CHECK] api_key=%s secret_key=%s configured=%s",
        "SET" if api_key else "MISSING",
        "SET" if secret_key else "MISSING",
        is_configured
    )
    return is_configured


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


def _esms_format_phone(phone_e164: str) -> str:
    """Convert E.164 phone (+84912345678) to eSMS.vn local format (0912345678).
    
    eSMS.vn expects Vietnamese numbers in local format starting with 0.
    """
    # Remove + and convert 84xxxxxxxxx to 0xxxxxxxxx
    if phone_e164.startswith("+84"):
        return "0" + phone_e164[3:]
    elif phone_e164.startswith("84"):
        return "0" + phone_e164[2:]
    # If already in local format or other format, return as is
    return phone_e164.lstrip("+")


def _mask_phone(phone: str | None) -> str:
    """Return a partially masked phone number for safe logging."""
    text = str(phone or "").strip()
    if len(text) < 4:
        return "***"
    return text[:3] + "***" + text[-2:]


def send_sms(to_phone: str, body: str) -> bool:
    """Send a plain-text SMS via eSMS.vn.

    Returns True on success, False otherwise.
    Skips sending gracefully when eSMS.vn is not configured.
    """
    logger.info("[SEND_SMS CALLED] to_phone=%s", _mask_phone(to_phone))
    
    if not is_twilio_configured():
        logger.warning("[SMS SKIPPED] reason=esms_not_configured")
        return False

    recipient_e164 = _normalize_phone(to_phone)
    if not recipient_e164:
        logger.warning("[SMS SKIPPED] reason=invalid_phone to_phone=%s", _mask_phone(to_phone))
        return False

    # Convert E.164 format to eSMS.vn local format (0912345678)
    recipient_local = _esms_format_phone(recipient_e164)
    logger.info("[SMS] Normalized phone: %s -> %s", _mask_phone(recipient_e164), _mask_phone(recipient_local))

    try:
        url = "https://rest.esms.vn/MainService.svc/json/SendMultipleMessage_V4_post_json/"
        payload = {
            "ApiKey": settings.esms_api_key,
            "SecretKey": settings.esms_secret_key,
            "Phone": recipient_local,
            "Content": body,
            "SmsType": 2,  # 2 = Brandname SMS (change to 1 for fixed number if needed)
        }
        
        # Log payload with masked keys
        safe_payload = {
            "ApiKey": settings.esms_api_key[:8] + "***" if settings.esms_api_key else "***",
            "SecretKey": "***",
            "Phone": _mask_phone(recipient_local),
            "Content": body[:50] + "..." if len(body) > 50 else body,
            "SmsType": payload["SmsType"],
        }
        logger.info("[ESMS PAYLOAD] %s", safe_payload)
        
        response = requests.post(url, json=payload, timeout=30)
        result = response.json()
        
        # Log complete response
        logger.info("[ESMS RESPONSE] status_code=%s body=%s", response.status_code, result)
        
        # eSMS.vn returns CodeResult: "100" for success
        code_result = str(result.get("CodeResult", ""))
        if code_result == "100":
            sms_id = result.get("SMSID", "unknown")
            logger.info("[SMS SENT] to=%s esms_id=%s", _mask_phone(recipient_local), sms_id)
            return True
        else:
            error_msg = result.get("ErrorMessage", "Unknown error")
            logger.error(
                "[SMS FAILED] to=%s esms_code=%s message=%s",
                _mask_phone(recipient_local), 
                code_result,
                error_msg
            )
            return False
            
    except requests.exceptions.RequestException as exc:
        logger.error("[SMS FAILED] to=%s network_error=%s", _mask_phone(recipient_local), str(exc))
        return False
    except Exception as exc:
        logger.exception("[SMS FAILED] to=%s unexpected_error=%s", _mask_phone(recipient_local), str(exc))
        return False
