# session_storage_manager.py
"""
Background refresh of taxpayer sessions.
GST sandbox sessions are valid for 6 hours; we refresh every 5h30m.
"""
import logging
import threading
from typing import Optional

# BUG FIX: Import from flat module names (no 'services.' prefix) to match project layout
from services.auth import refresh_session
from session_storage import get_all_sessions, get_session

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_SECONDS = 5 * 3600 + 30 * 60  # 5h 30m
_stop_event = threading.Event()
_thread: Optional[threading.Thread] = None


def _refresh_all_sessions():
    sessions = get_all_sessions()
    for gstin in list(sessions.keys()):
        try:
            result = refresh_session(gstin)
            if result.get("success"):
                logger.info("auto_refresh_ok gstin=%s***%s", gstin[:2], gstin[-4:])
            else:
                logger.warning(
                    "auto_refresh_failed gstin=%s***%s msg=%s",
                    gstin[:2], gstin[-4:], result.get("message"),
                )
        except Exception as exc:
            logger.exception("auto_refresh_exception gstin=%s***%s error=%s", gstin[:2], gstin[-4:], exc)


def _scheduler_loop():
    logger.info("session_scheduler_started interval=%ds", REFRESH_INTERVAL_SECONDS)
    while not _stop_event.wait(timeout=REFRESH_INTERVAL_SECONDS):
        _refresh_all_sessions()
    logger.info("session_scheduler_stopped")


def start_scheduler():
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_scheduler_loop, daemon=True, name="SessionRefresher")
    _thread.start()


def stop_scheduler():
    _stop_event.set()


def manual_refresh(gstin: str) -> dict:
    """Trigger an immediate session refresh for a single GSTIN."""
    return refresh_session(gstin)