# session_storage.py
import json
import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# { GSTIN: { access_token, refresh_token, token_expiry, session_expiry, username, last_refresh } }
sessions: Dict[str, Dict[str, Any]] = {}


def _normalize_gstin(gstin: str) -> str:
    return (gstin or "").strip().upper()


def _mask_gstin(gstin: str) -> str:
    if not gstin:
        return "unknown"
    if len(gstin) <= 6:
        return "***"
    return f"{gstin[:2]}***{gstin[-4:]}"


def _session_file_path(gstin: str) -> str:
    return os.path.join("sessions", f"{gstin}_session.json")


def _to_epoch_seconds(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None

    if isinstance(value, (int, float)):
        ts = float(value)
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            ts = float(stripped)
        except ValueError:
            return None
    else:
        return None

    # Convert milliseconds to seconds when needed.
    if ts > 1_000_000_000_000:
        ts = ts / 1000.0

    return ts


def _is_session_expired(session: Dict[str, Any]) -> bool:
    # Prefer session expiry; fallback to token expiry.
    session_expiry = _to_epoch_seconds(session.get("session_expiry"))
    token_expiry = _to_epoch_seconds(session.get("token_expiry"))

    expiry = session_expiry or token_expiry
    if not expiry:
        return False

    return time.time() >= expiry


def save_session(
    gstin: str,
    access_token: str,
    refresh_token: str = None,
    token_expiry: Any = None,
    session_expiry: Any = None,
    username: str = None,
):
    gstin = _normalize_gstin(gstin)
    if not gstin:
        logger.warning("session_save_skipped invalid_gstin")
        return

    existing = sessions.get(gstin, {})
    sessions[gstin] = {
        "access_token": access_token,
        "refresh_token": refresh_token or existing.get("refresh_token"),
        "token_expiry": token_expiry or existing.get("token_expiry"),
        "session_expiry": session_expiry or existing.get("session_expiry"),
        "username": username or existing.get("username"),
        "last_refresh": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    logger.info("session_saved gstin=%s", _mask_gstin(gstin))

    try:
        os.makedirs("sessions", exist_ok=True)
        with open(_session_file_path(gstin), "w", encoding="utf-8") as f:
            json.dump(sessions[gstin], f)
    except Exception as e:
        logger.exception("session_save_to_disk_failed gstin=%s error=%s", gstin, e)


def get_session(gstin: str) -> Dict[str, Any] | None:
    gstin = _normalize_gstin(gstin)
    if not gstin:
        return None

    in_memory = sessions.get(gstin)
    if in_memory:
        if _is_session_expired(in_memory):
            logger.info("session_expired_in_memory gstin=%s", _mask_gstin(gstin))
            delete_session(gstin)
            return None
        return in_memory

    try:
        with open(_session_file_path(gstin), "r", encoding="utf-8") as f:
            loaded = json.load(f)

        if not isinstance(loaded, dict):
            logger.warning("session_disk_invalid_format gstin=%s", _mask_gstin(gstin))
            return None

        if _is_session_expired(loaded):
            logger.info("session_expired_on_disk gstin=%s", _mask_gstin(gstin))
            delete_session(gstin)
            return None

        sessions[gstin] = loaded
        return loaded
    except FileNotFoundError:
        return None
    except Exception as e:
        logger.exception("get_session_error gstin=%s error=%s", gstin, e)
        return None


def get_all_sessions() -> Dict[str, Dict[str, Any]]:
    active: Dict[str, Dict[str, Any]] = {}
    for gstin, session in list(sessions.items()):
        if _is_session_expired(session):
            delete_session(gstin)
            continue
        active[gstin] = dict(session)
    return active


def delete_session(gstin: str):
    gstin = _normalize_gstin(gstin)
    if not gstin:
        return

    removed = False
    if gstin in sessions:
        del sessions[gstin]
        removed = True

    path = _session_file_path(gstin)
    try:
        if os.path.exists(path):
            os.remove(path)
            removed = True
    except Exception:
        logger.exception("failed_remove_session_file gstin=%s", gstin)

    if removed:
        logger.info("session_deleted gstin=%s", _mask_gstin(gstin))
