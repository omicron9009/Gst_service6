from __future__ import annotations

import functools
import logging
from typing import Any, Callable

from .persistence_auth import AUTH_PERSISTERS
from .persistence_common import deactivate_client_session_by_gstin, run_async
from .persistence_gstr1 import GSTR1_PERSISTERS
from .persistence_gstr2a import GSTR2A_PERSISTERS
from .persistence_gstr2b import GSTR2B_PERSISTERS
from .persistence_gstr3b import GSTR3B_PERSISTERS
from .persistence_gstr9 import GSTR9_PERSISTERS
from .persistence_ledger import LEDGER_PERSISTERS
from .persistence_return_status import RETURN_STATUS_PERSISTERS


logger = logging.getLogger(__name__)

PERSISTERS: dict[str, Callable[[tuple[Any, ...], dict[str, Any], Any], None]] = {}
PERSISTERS.update(AUTH_PERSISTERS)
PERSISTERS.update(GSTR1_PERSISTERS)
PERSISTERS.update(GSTR2A_PERSISTERS)
PERSISTERS.update(GSTR2B_PERSISTERS)
PERSISTERS.update(GSTR3B_PERSISTERS)
PERSISTERS.update(GSTR9_PERSISTERS)
PERSISTERS.update(LEDGER_PERSISTERS)
PERSISTERS.update(RETURN_STATUS_PERSISTERS)


def _extract_upstream_status_code(result: dict[str, Any]) -> int | None:
    upstream_status_code = result.get("upstream_status_code") or result.get("status_code")
    try:
        if upstream_status_code is not None:
            return int(upstream_status_code)
    except (TypeError, ValueError):
        pass

    for raw_key in ("raw", "response", "upstream_response"):
        raw_payload = result.get(raw_key)
        if not isinstance(raw_payload, dict):
            continue
        raw_code = raw_payload.get("code") or raw_payload.get("status_code") or raw_payload.get("status")
        try:
            if raw_code is not None:
                return int(raw_code)
        except (TypeError, ValueError):
            continue

    return None


def _extract_upstream_error_code(payload: dict[str, Any]) -> str | None:
    for raw_key in ("raw", "response", "upstream_response"):
        raw_payload = payload.get(raw_key)
        if not isinstance(raw_payload, dict):
            continue
        error_obj = raw_payload.get("error")
        if isinstance(error_obj, dict) and error_obj.get("error_cd"):
            return str(error_obj["error_cd"])
        data_obj = raw_payload.get("data")
        if isinstance(data_obj, dict):
            nested_error = data_obj.get("error")
            if isinstance(nested_error, dict) and nested_error.get("error_cd"):
                return str(nested_error["error_cd"])
    return None


def _extract_upstream_message(payload: dict[str, Any], fallback_status: int | None) -> str:
    for raw_key in ("raw", "response", "upstream_response"):
        raw_payload = payload.get(raw_key)
        if not isinstance(raw_payload, dict):
            continue
        for key in ("message", "msg", "detail", "error_description"):
            value = raw_payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        data_obj = raw_payload.get("data")
        if isinstance(data_obj, dict):
            error_obj = data_obj.get("error")
            if isinstance(error_obj, dict):
                message = error_obj.get("message")
                if isinstance(message, str) and message.strip():
                    return message.strip()

    if fallback_status is not None:
        return f"GST API request failed with status {fallback_status}."
    return "GST API request failed."


def _normalize_service_result(result: Any) -> Any:
    if not isinstance(result, dict) or result.get("success") is not True:
        return result

    upstream_status_code = _extract_upstream_status_code(result)
    if upstream_status_code is None or upstream_status_code < 400:
        return result

    normalized = dict(result)
    normalized["success"] = False
    normalized["upstream_status_code"] = upstream_status_code
    normalized.setdefault("status_code", upstream_status_code)
    normalized["message"] = _extract_upstream_message(normalized, upstream_status_code)

    error_code = _extract_upstream_error_code(normalized)
    if error_code:
        normalized.setdefault("error_code", error_code)

    return normalized


def persist_service_result(handler_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    handler = PERSISTERS.get(handler_name)
    if handler is None:
        raise ValueError(f"Unknown persistence handler: {handler_name}")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = _normalize_service_result(func(*args, **kwargs))
            try:
                handler(args, kwargs, result)
            except Exception:
                logger.exception("db_persistence_failed handler=%s", handler_name)
            return result

        return wrapper

    return decorator


def sync_deactivate_client_session(gstin: str) -> None:
    if not gstin:
        return
    run_async(lambda: deactivate_client_session_by_gstin(gstin))
