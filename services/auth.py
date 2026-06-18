# services/auth.py
import base64
import json
import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

import config
from session_storage import get_session, save_session
from database.core.database import get_sync_db
from database.models.client import Client

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 30
TOKEN_REFRESH_BUFFER_SECONDS = 60
OTP_CONTEXT_TTL_SECONDS = 10 * 60

_platform_access_token: Optional[str] = None
_platform_access_token_expiry_epoch: float = 0.0

# Stores the authorization token used to generate OTP per (gstin, username)
# so that verify uses the same auth context.
_otp_auth_context: Dict[str, Dict[str, Any]] = {}


def invalidate_platform_token() -> None:
    """Clear the cached Sandbox platform token so the next call re-authenticates."""
    global _platform_access_token, _platform_access_token_expiry_epoch
    _platform_access_token = None
    _platform_access_token_expiry_epoch = 0.0


def _ensure_client_in_db(gstin: str, username: str) -> None:
    """Insert or update a Client row in PG so the DB proxy can list it."""
    try:
        db = get_sync_db()
        try:
            client = db.query(Client).filter(Client.gstin == gstin).first()
            if client:
                if username and not client.username:
                    client.username = username
                if not client.is_active:
                    client.is_active = True
            else:
                client = Client(gstin=gstin, username=username or "", is_active=True)
                db.add(client)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    except Exception as exc:
        logger.warning("ensure_client_in_db_failed gstin=%s error=%s", gstin[:4] + "***", exc)


def _mask_gstin(gstin: str) -> str:
    if not gstin:
        return "unknown"
    if len(gstin) <= 6:
        return "***"
    return f"{gstin[:2]}***{gstin[-4:]}"


def _normalize_gstin(gstin: str) -> str:
    return (gstin or "").strip().upper()


def _otp_context_key(username: str, gstin: str) -> str:
    return f"{_normalize_gstin(gstin)}::{(username or '').strip().lower()}"


def _save_otp_context(username: str, gstin: str, authorization_token: str) -> None:
    if not authorization_token:
        return
    _otp_auth_context[_otp_context_key(username, gstin)] = {
        "authorization": authorization_token,
        "created_at": time.time(),
    }


def _get_otp_context_token(username: str, gstin: str) -> Optional[str]:
    key = _otp_context_key(username, gstin)
    record = _otp_auth_context.get(key)
    if not record:
        return None

    created_at = float(record.get("created_at") or 0.0)
    if created_at and (time.time() - created_at) > OTP_CONTEXT_TTL_SECONDS:
        _otp_auth_context.pop(key, None)
        return None

    token = record.get("authorization")
    return token if isinstance(token, str) and token else None


def _clear_otp_context(username: str, gstin: str) -> None:
    _otp_auth_context.pop(_otp_context_key(username, gstin), None)


def _safe_json(response: requests.Response) -> Dict[str, Any]:
    try:
        parsed = response.json()
        return parsed if isinstance(parsed, dict) else {"payload": parsed}
    except ValueError:
        return {"raw_text": response.text}


def _extract_message(payload: Dict[str, Any], fallback: str) -> str:
    for key in ("message", "msg", "status_desc", "detail", "error"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    data = payload.get("data")
    if isinstance(data, dict):
        error_obj = data.get("error")
        if isinstance(error_obj, dict):
            error_msg = error_obj.get("message")
            if isinstance(error_msg, str) and error_msg.strip():
                return error_msg.strip()

    return fallback


def _extract_status_cd(payload: Dict[str, Any]) -> Optional[str]:
    if "status_cd" in payload:
        return str(payload.get("status_cd"))

    data = payload.get("data")
    if isinstance(data, dict) and "status_cd" in data:
        return str(data.get("status_cd"))

    return None


def _extract_error_code(payload: Dict[str, Any]) -> Optional[str]:
    data = payload.get("data")
    if isinstance(data, dict):
        error_obj = data.get("error")
        if isinstance(error_obj, dict) and error_obj.get("error_cd"):
            return str(error_obj["error_cd"])

    error_obj = payload.get("error")
    if isinstance(error_obj, dict) and error_obj.get("error_cd"):
        return str(error_obj["error_cd"])

    return None


def _decode_jwt_expiry_epoch(token: str) -> Optional[int]:
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None

        payload_b64 = parts[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)

        decoded = base64.urlsafe_b64decode(payload_b64.encode("ascii")).decode("utf-8")
        payload = json.loads(decoded)
        exp = payload.get("exp")
        return int(exp) if exp else None
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def _authenticate_platform(force_refresh: bool = False) -> str:
    global _platform_access_token, _platform_access_token_expiry_epoch

    now = time.time()
    if not force_refresh and _platform_access_token and now < _platform_access_token_expiry_epoch:
        return _platform_access_token

    auth_url = f"{config.BASE_URL}/authenticate"
    auth_headers = {
        "x-api-key": config.API_KEY,
        "x-api-secret": config.API_SECRET,
        "x-api-version": config.API_VERSION,
    }

    try:
        response = requests.post(auth_url, headers=auth_headers, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise RuntimeError(f"Platform authentication request failed: {exc}") from exc

    response_payload = _safe_json(response)

    if response.status_code >= 400:
        message = _extract_message(response_payload, "Platform authentication failed.")
        raise RuntimeError(f"{message} (status={response.status_code})")

    token = response_payload.get("data", {}).get("access_token")
    if not token:
        message = _extract_message(response_payload, "Access token missing in /authenticate response.")
        raise RuntimeError(message)

    expiry_epoch = _decode_jwt_expiry_epoch(token)
    if expiry_epoch:
        _platform_access_token_expiry_epoch = max(now + 30, expiry_epoch - TOKEN_REFRESH_BUFFER_SECONDS)
    else:
        # Conservative fallback if token does not expose exp.
        _platform_access_token_expiry_epoch = now + (24 * 60 * 60)

    _platform_access_token = token
    return token


def _platform_headers_with_token(token: str) -> Dict[str, str]:
    return {
        "Authorization": token,
        "x-api-key": config.API_KEY,
        "x-api-version": config.API_VERSION,
        "x-source": "primary",
        "Content-Type": "application/json",
    }


def _platform_headers(force_refresh: bool = False) -> Dict[str, str]:
    token = _authenticate_platform(force_refresh=force_refresh)
    return _platform_headers_with_token(token)


def _post_with_platform_auth(
    url: str,
    payload: Dict[str, Any],
    *,
    authorization_token: Optional[str] = None,
    retry_on_auth_error: bool = True,
) -> tuple[requests.Response, str]:
    """
    POST with platform token.
    Returns (response, authorization_token_used).
    """
    token_used = authorization_token or _authenticate_platform()
    response = requests.post(
        url,
        json=payload,
        headers=_platform_headers_with_token(token_used),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    try:
        data = response.json()
    except Exception:
        return response, token_used

    error_cd = data.get("data", {}).get("error", {}).get("error_cd")

    # Retry for auth errors only when token is not explicitly pinned.
    if retry_on_auth_error and not authorization_token and (error_cd == "AUTH4033" or response.status_code in (401, 403)):
        logger.warning("Platform token expired (error_cd=%s). Force re-authenticating...", error_cd)
        token_used = _authenticate_platform(force_refresh=True)
        response = requests.post(
            url,
            json=payload,
            headers=_platform_headers_with_token(token_used),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

    return response, token_used


def generate_otp(username: str, gstin: str) -> Dict[str, Any]:
    username = (username or "").strip()
    gstin = _normalize_gstin(gstin)
    masked_gstin = _mask_gstin(gstin)

    logger.info("otp_generate_started gstin=%s username=%s", masked_gstin, username)

    url = f"{config.BASE_URL}/gst/compliance/tax-payer/otp"
    payload = {"username": username, "gstin": gstin}

    try:
        response, authorization_token_used = _post_with_platform_auth(url, payload)
    except (requests.RequestException, RuntimeError) as exc:
        logger.exception("otp_generate_failed gstin=%s error=%s", masked_gstin, exc)
        return {
            "request_sent": False,
            "success": False,
            "message": "Unable to send OTP request to GST API.",
            "error": str(exc),
        }

    response_payload = _safe_json(response)
    status_cd = _extract_status_cd(response_payload)
    success = (200 <= response.status_code < 300) and (status_cd in (None, "1"))
    error_code = _extract_error_code(response_payload)

    fallback_message = "OTP request sent. Check your registered mobile or email." if success else "OTP request failed."
    message = _extract_message(response_payload, fallback_message)

    if success:
        _save_otp_context(username, gstin, authorization_token_used)
    else:
        _clear_otp_context(username, gstin)

    logger.info(
        "otp_generate_completed gstin=%s status_code=%s status_cd=%s success=%s",
        masked_gstin,
        response.status_code,
        status_cd,
        success,
    )

    return {
        "request_sent": True,
        "success": success,
        "message": message,
        "error_code": error_code,
        "status_cd": status_cd,
        "upstream_status_code": response.status_code,
        "upstream_response": response_payload,
    }


def verify_otp(username: str, gstin: str, otp: str) -> Dict[str, Any]:
    username = (username or "").strip()
    gstin = _normalize_gstin(gstin)
    otp = (otp or "").strip()
    masked_gstin = _mask_gstin(gstin)

    logger.info("otp_verify_started gstin=%s username=%s", masked_gstin, username)

    # OTP is a query parameter as per the current Sandbox API docs.
    url = f"{config.BASE_URL}/gst/compliance/tax-payer/otp/verify?{urlencode({'otp': otp})}"
    payload = {"username": username, "gstin": gstin}

    otp_context_token = _get_otp_context_token(username, gstin)
    if otp_context_token:
        logger.info("otp_verify_using_cached_context gstin=%s", masked_gstin)
    else:
        logger.warning(
            "otp_verify_context_missing gstin=%s; using current platform token",
            masked_gstin,
        )

    try:
        response, _ = _post_with_platform_auth(
            url,
            payload,
            authorization_token=otp_context_token,
            retry_on_auth_error=otp_context_token is None,
        )
    except (requests.RequestException, RuntimeError) as exc:
        logger.exception("otp_verify_failed gstin=%s error=%s", masked_gstin, exc)
        return {
            "request_sent": False,
            "success": False,
            "message": "Unable to send OTP verification request to GST API.",
            "error": str(exc),
        }
    finally:
        # OTP verification is a one-time flow; require a fresh OTP generate for a new attempt.
        _clear_otp_context(username, gstin)

    response_payload = _safe_json(response)
    data = response_payload.get("data", {})
    status_cd = _extract_status_cd(response_payload)
    api_success = (200 <= response.status_code < 300) and (status_cd in (None, "1"))

    token = data.get("access_token") if isinstance(data, dict) else None
    refresh_token = data.get("refresh_token") if isinstance(data, dict) else None
    token_expiry = data.get("token_expiry") if isinstance(data, dict) else None
    session_expiry = data.get("session_expiry") if isinstance(data, dict) else None
    session_saved = False

    if api_success and token:
        save_session(gstin, token, refresh_token, token_expiry, session_expiry, username)
        _ensure_client_in_db(gstin, username)
        session_saved = True

    success = api_success and session_saved
    error_code = _extract_error_code(response_payload)

    if success:
        fallback_message = "OTP verified and GST session saved."
    elif api_success:
        fallback_message = "OTP verified, but GST access token was not found in response."
    elif error_code == "AUTH4033":
        fallback_message = "Invalid session. Generate OTP again and verify with the latest OTP."
    else:
        fallback_message = "OTP verification failed."

    logger.info(
        "otp_verify_completed gstin=%s status_code=%s status_cd=%s success=%s session_saved=%s",
        masked_gstin,
        response.status_code,
        status_cd,
        success,
        session_saved,
    )

    return {
        "request_sent": True,
        "success": success,
        "session_saved": session_saved,
        "message": _extract_message(response_payload, fallback_message),
        "error_code": error_code,
        "status_cd": status_cd,
        "upstream_status_code": response.status_code,
        "data": data,
        "upstream_response": response_payload,
    }


def refresh_session(gstin: str) -> Dict[str, Any]:
    """
    Extends taxpayer session by 6 hours without re-OTP.
    Uses the taxpayer access_token in Authorization.
    """
    gstin = _normalize_gstin(gstin)
    masked_gstin = _mask_gstin(gstin)

    logger.info("session_refresh_started gstin=%s", masked_gstin)

    session = get_session(gstin)
    if not session or not session.get("access_token"):
        return {
            "request_sent": False,
            "success": False,
            "message": "No active session found for GSTIN. Verify OTP first.",
        }

    url = f"{config.BASE_URL}/gst/compliance/tax-payer/session/refresh"
    headers = {
        "Authorization": session["access_token"],
        "x-api-key": config.API_KEY,
        "x-api-version": config.API_VERSION,
        "x-source": "primary",
    }

    try:
        response = requests.post(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        logger.exception("session_refresh_failed gstin=%s error=%s", masked_gstin, exc)
        return {
            "request_sent": False,
            "success": False,
            "message": "Unable to refresh GST session.",
            "error": str(exc),
        }

    response_payload = _safe_json(response)
    data = response_payload.get("data", {})
    status_cd = _extract_status_cd(response_payload)
    api_success = (200 <= response.status_code < 300) and (status_cd in (None, "1"))

    new_token = data.get("access_token") if isinstance(data, dict) else None
    new_refresh_token = data.get("refresh_token") if isinstance(data, dict) else None
    token_expiry = data.get("token_expiry") if isinstance(data, dict) else None
    session_expiry = data.get("session_expiry") if isinstance(data, dict) else None
    session_saved = False

    if api_success:
        # Some refresh responses extend expiry without a new token.
        token_to_save = new_token or session.get("access_token")
        if token_to_save:
            save_session(
                gstin,
                token_to_save,
                new_refresh_token or session.get("refresh_token"),
                token_expiry or session.get("token_expiry"),
                session_expiry or session.get("session_expiry"),
                session.get("username"),
            )
            session_saved = True

    success = api_success and session_saved
    error_code = _extract_error_code(response_payload)

    if success:
        fallback_message = "Session refreshed successfully."
    elif api_success:
        fallback_message = "Session refresh completed but token missing in response."
    else:
        fallback_message = "Session refresh failed."

    logger.info(
        "session_refresh_completed gstin=%s status_code=%s success=%s session_saved=%s",
        masked_gstin,
        response.status_code,
        success,
        session_saved,
    )

    return {
        "request_sent": True,
        "success": success,
        "session_saved": session_saved,
        "message": _extract_message(response_payload, fallback_message),
        "error_code": error_code,
        "status_cd": status_cd,
        "upstream_status_code": response.status_code,
        "data": data,
        "upstream_response": response_payload,
    }
