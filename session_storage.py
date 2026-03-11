# session_storage.py
import logging
import time
import json
import os

logger = logging.getLogger(__name__)

# { gstin: { access_token, refresh_token, token_expiry, session_expiry, username, last_refresh } }
sessions: dict = {}


def save_session(
    gstin: str,
    access_token: str,
    refresh_token: str = None,
    token_expiry=None,
    session_expiry=None,
    username: str = None,
):
    existing = sessions.get(gstin, {})
    sessions[gstin] = {
        "access_token": access_token,
        "refresh_token": refresh_token or existing.get("refresh_token"),
        "token_expiry": token_expiry or existing.get("token_expiry"),
        "session_expiry": session_expiry or existing.get("session_expiry"),
        "username": username or existing.get("username"),
        "last_refresh": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    logger.info("session_saved gstin=%s***%s", gstin[:2], gstin[-4:])
    try:
        os.makedirs("sessions", exist_ok=True)
        # BUG FIX: json.dump requires the file handle as second argument
        with open(f"sessions/{gstin}_session.json", "w", encoding="utf-8") as f:
            json.dump(sessions[gstin], f)
    except Exception as e:
        logger.exception("session_save_to_disk_failed gstin=%s error=%s", gstin, e)


def get_session(gstin: str) -> dict | None:
    # BUG FIX: typo `_essions` → `sessions`
    if gstin in sessions:
        return sessions[gstin]

    # Fallback: try to load from disk file written by save_session
    try:
        with open(f"sessions/{gstin}_session.json", "r", encoding="utf-8") as f:
            curr_session = json.load(f)
            # cache in memory
            sessions[gstin] = curr_session
            return curr_session
    except FileNotFoundError:
        return None
    except Exception as e:
        logger.exception("get_session_error gstin=%s error=%s", gstin, e)
        return None


def get_all_sessions() -> dict:
    return dict(sessions)


def delete_session(gstin: str):
    if gstin in sessions:
        del sessions[gstin]
        logger.info("session_deleted gstin=%s***%s", gstin[:2], gstin[-4:])
    try:
        import os

        path = f"{gstin}_session.json"
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        logger.exception("failed_remove_session_file gstin=%s", gstin)