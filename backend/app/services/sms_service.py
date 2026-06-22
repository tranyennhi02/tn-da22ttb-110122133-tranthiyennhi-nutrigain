from __future__ import annotations

import logging
import re
import time

import requests
from requests.auth import HTTPBasicAuth

from app.core.config import settings


logger = logging.getLogger(__name__)


# Global token cache with expiration tracking
_cached_token: str | None = None
_token_expires_at: float = 0.0  # Unix timestamp


def is_smsgate_configured() -> bool:
    """Return True only when SMSGate is properly configured with credentials."""
    is_configured = bool(
        settings.smsgate_url 
        and settings.smsgate_username 
        and settings.smsgate_password
    )
    
    logger.info(
        "[SMSGATE CONFIG CHECK] url=%s username=%s password=%s configured=%s",
        "SET" if settings.smsgate_url else "MISSING",
        "SET" if settings.smsgate_username else "MISSING",
        "SET" if settings.smsgate_password else "MISSING",
        is_configured
    )
    return is_configured


# Legacy function name for backward compatibility
def is_twilio_configured() -> bool:
    """Legacy function name - redirects to is_smsgate_configured()."""
    return is_smsgate_configured()


def _mask_token(token: str | None) -> str:
    """Return a partially masked token for safe logging."""
    if not token or len(token) < 20:
        return "***"
    return token[:10] + "***"


def _get_token() -> str | None:
    """Get JWT token from SMSGate using HTTP Basic Auth + scope-based JWT.
    
    Authentication flow:
    1. Use HTTP Basic Auth (username/password) to authenticate
    2. Request JWT token with scopes
    3. Cache token until expiration
    
    Returns the token string on success, None on failure.
    """
    global _cached_token, _token_expires_at
    
    # Return cached token if available and not expired
    current_time = time.time()
    if _cached_token and current_time < _token_expires_at:
        logger.debug("[SMSGATE TOKEN] Using cached token (expires in %.0fs)", _token_expires_at - current_time)
        return _cached_token
    
    try:
        token_url = f"{settings.smsgate_url}/auth/token"
        payload = {
            "scopes": ["devices:list", "messages:send", "inbox:read"],
            "ttl": 3600
        }
        
        # Create Basic Auth credentials
        basic_auth = HTTPBasicAuth(settings.smsgate_username, settings.smsgate_password)
        
        logger.info("[SMSGATE TOKEN REQUEST] POST %s (with Basic Auth)", token_url)
        logger.debug("[SMSGATE TOKEN PAYLOAD] %s", payload)
        logger.debug("[SMSGATE BASIC AUTH] username=%s", settings.smsgate_username)
        
        # Call /auth/token with Basic Auth
        response = requests.post(
            token_url, 
            json=payload, 
            auth=basic_auth,  # CRITICAL: Basic Auth required here
            timeout=5
        )
        
        logger.info("[SMSGATE TOKEN RESPONSE] status_code=%s", response.status_code)
        
        # Accept both 200 OK and 201 Created as success
        if response.status_code not in (200, 201):
            logger.error(
                "[SMSGATE TOKEN FAILED] status_code=%s headers=%s body=%s",
                response.status_code,
                dict(response.headers),
                response.text[:500]
            )
            
            if response.status_code == 401:
                logger.error(
                    "[SMSGATE TOKEN FAILED] 401 Unauthorized - Check username/password credentials. "
                    "SMSGate requires HTTP Basic Auth before issuing JWT token."
                )
            
            return None
        
        try:
            result = response.json()
        except ValueError as json_err:
            logger.error("[SMSGATE TOKEN FAILED] Invalid JSON response: %s. Body: %s", json_err, response.text[:500])
            return None
        
        if "access_token" not in result:
            logger.error("[SMSGATE TOKEN FAILED] Missing 'access_token' in response: %s", result)
            return None
        
        _cached_token = result["access_token"]
        # Set expiration 60 seconds before actual TTL to avoid edge cases
        _token_expires_at = current_time + (payload["ttl"] - 60)
        
        logger.info(
            "[SMSGATE TOKEN SUCCESS] Obtained JWT token: %s (expires in %ds)",
            _mask_token(_cached_token),
            payload["ttl"]
        )
        return _cached_token
            
    except requests.exceptions.Timeout:
        logger.error("[SMSGATE TOKEN FAILED] Request timeout after 5s")
        return None
    except requests.exceptions.ConnectionError as exc:
        logger.error("[SMSGATE TOKEN FAILED] Connection error: %s. Is SMSGate server running?", str(exc))
        return None
    except requests.exceptions.RequestException as exc:
        logger.error("[SMSGATE TOKEN FAILED] Network error: %s", str(exc))
        return None
    except Exception as exc:
        logger.exception("[SMSGATE TOKEN FAILED] Unexpected error: %s", str(exc))
        return None


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
    """Send a plain-text SMS via SMSGate local API.
    
    Authentication flow:
    1. Get JWT token using Basic Auth + scopes
    2. Send SMS using Bearer token
    3. Retry once if 401 (token expired)

    Returns True on success, False otherwise.
    Skips sending gracefully when SMSGate is not configured.
    """
    global _cached_token, _token_expires_at
    
    logger.info("[SEND_SMS CALLED] to_phone=%s", _mask_phone(to_phone))
    
    if not is_smsgate_configured():
        logger.warning("[SMS SKIPPED] reason=smsgate_not_configured")
        return False

    recipient_e164 = _normalize_phone(to_phone)
    if not recipient_e164:
        logger.warning("[SMS SKIPPED] reason=invalid_phone to_phone=%s", _mask_phone(to_phone))
        return False

    logger.info("[SMS] Normalized phone: %s", _mask_phone(recipient_e164))

    # Attempt SMS sending with retry on 401
    max_attempts = 2
    for attempt in range(1, max_attempts + 1):
        # Get authentication token (with Basic Auth)
        token = _get_token()
        if not token:
            logger.error("[SMS FAILED] reason=token_acquisition_failed attempt=%d/%d", attempt, max_attempts)
            if attempt < max_attempts:
                logger.info("[SMS RETRY] Attempting to refresh token...")
                _cached_token = None
                _token_expires_at = 0.0
                continue
            return False

        # Validate message is not empty
        if not body or not body.strip():
            logger.error("[SMS FAILED] reason=empty_message")
            return False

        try:
            messages_url = f"{settings.smsgate_url}/messages"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            
            # CRITICAL: Use EXACT OpenAPI schema from SMSGate Swagger
            # POST /messages request body schema:
            # {
            #   "message": "<string>",
            #   "phoneNumbers": ["<string>"],
            #   "priority": 0
            # }
            # 
            # DO NOT use: recipients, dataMessage, textMessage, or any wrapper
            payload = {
                "message": str(body.strip()),      # String: SMS text content
                "phoneNumbers": [recipient_e164],  # Array: List of phone numbers
                "priority": 0                      # Integer: Default priority
            }
            
            # Log payload with masked data
            safe_payload = {
                "message": body[:50] + "..." if len(body) > 50 else body,
                "phoneNumbers": [_mask_phone(recipient_e164)],
                "priority": 0
            }
            logger.info("[SMSGATE SEND REQUEST] attempt=%d/%d payload=%s", attempt, max_attempts, safe_payload)
            logger.debug("[SMSGATE AUTH HEADER] token=%s", _mask_token(token))
            print(f"[SMSGATE FULL PAYLOAD] {payload}")
            
            response = requests.post(messages_url, json=payload, headers=headers, timeout=5)
            
            # Log response
            logger.info("[SMSGATE SEND RESPONSE] status_code=%s attempt=%d/%d", response.status_code, attempt, max_attempts)
            print(f"[SMSGATE RESPONSE] status={response.status_code} body={response.text[:200]}")
            
            # SMSGate returns 200, 201, or 202 for success
            if response.status_code in (200, 201, 202):
                logger.info("[SMS SENT SUCCESS] to=%s status_code=%s", _mask_phone(recipient_e164), response.status_code)
                return True
            elif response.status_code == 400:
                # Bad Request - payload schema error, do NOT retry
                logger.error(
                    "[SMS FAILED] 400 Bad Request - Invalid payload schema. body=%s",
                    response.text[:500]
                )
                return False
            elif response.status_code == 401:
                # Token expired or invalid, clear cache and retry
                logger.warning(
                    "[SMS FAILED] 401 Unauthorized - Token invalid/expired. attempt=%d/%d",
                    attempt, max_attempts
                )
                _cached_token = None
                _token_expires_at = 0.0
                
                if attempt < max_attempts:
                    logger.info("[SMS RETRY] Refreshing token and retrying...")
                    continue
                else:
                    logger.error("[SMS FAILED] Max retries reached after 401")
                    return False
            elif response.status_code == 500:
                # Server error - log and retry if attempts left
                logger.error(
                    "[SMS FAILED] 500 Server Error. body=%s attempt=%d/%d",
                    response.text[:500],
                    attempt,
                    max_attempts
                )
                
                if attempt < max_attempts:
                    logger.info("[SMS RETRY] Retrying after server error...")
                    continue
                return False
            else:
                # Other errors - log and don't retry
                logger.error(
                    "[SMS FAILED] to=%s status_code=%s body=%s attempt=%d/%d",
                    _mask_phone(recipient_e164),
                    response.status_code,
                    response.text[:500],
                    attempt,
                    max_attempts
                )
                return False
                
        except requests.exceptions.Timeout:
            logger.error("[SMS FAILED] to=%s timeout after 5s attempt=%d/%d", _mask_phone(recipient_e164), attempt, max_attempts)
            if attempt < max_attempts:
                continue
            return False
        except requests.exceptions.ConnectionError as exc:
            logger.error("[SMS FAILED] to=%s connection_error=%s attempt=%d/%d", _mask_phone(recipient_e164), str(exc), attempt, max_attempts)
            if attempt < max_attempts:
                continue
            return False
        except requests.exceptions.RequestException as exc:
            logger.error("[SMS FAILED] to=%s network_error=%s attempt=%d/%d", _mask_phone(recipient_e164), str(exc), attempt, max_attempts)
            if attempt < max_attempts:
                continue
            return False
        except Exception as exc:
            logger.exception("[SMS FAILED] to=%s unexpected_error=%s attempt=%d/%d", _mask_phone(recipient_e164), str(exc), attempt, max_attempts)
            return False
    
    # Should not reach here, but safety fallback
    return False
