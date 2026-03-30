from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update

from .persistence_common import (
    CLIENT_SESSIONS,
    append_otp_request,
    as_dict,
    current_session_snapshot,
    deactivate_active_sessions,
    ensure_client,
    insert_active_session,
    run_async,
    run_in_session,
    sentinel,
    to_datetime,
)


OTP_CONTEXT_TTL_SECONDS = 10 * 60


def persist_generate_otp(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    upstream_response = as_dict(result.get("upstream_response"))
    message = (
        result.get("message")
        or upstream_response.get("message")
        or result.get("error")
    )

    async def work(session) -> None:
        username = sentinel(kwargs.get("username") or (args[0] if args else ""))
        gstin = sentinel(kwargs.get("gstin") or (args[1] if len(args) > 1 else ""))
        if not gstin:
            return

        client_id = await ensure_client(session, gstin, username)
        await append_otp_request(
            session,
            client_id=client_id,
            status="pending" if result.get("success") else "failed",
            upstream_status_cd=sentinel(result.get("status_cd")) or None,
            message=sentinel(message) or None,
            expires_at=(
                datetime.now(timezone.utc) + timedelta(seconds=OTP_CONTEXT_TTL_SECONDS)
                if result.get("success")
                else None
            ),
        )

    run_async(lambda: run_in_session(work))


def persist_verify_otp(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    data = as_dict(result.get("data"))
    upstream_response = as_dict(result.get("upstream_response"))
    message = (
        result.get("message")
        or upstream_response.get("message")
        or result.get("error")
    )

    async def work(session) -> None:
        username = sentinel(kwargs.get("username") or (args[0] if args else ""))
        gstin = sentinel(kwargs.get("gstin") or (args[1] if len(args) > 1 else ""))
        if not gstin:
            return

        client_id = await ensure_client(session, gstin, username)
        await append_or_update_otp_after_verification(
            session=session,
            client_id=client_id,
            success=bool(result.get("success")),
            status_cd=sentinel(result.get("status_cd")) or None,
            message=sentinel(message) or None,
        )

        if not result.get("success"):
            return

        snapshot = current_session_snapshot(gstin)
        if not snapshot and data:
            snapshot = {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "token_expiry": data.get("token_expiry"),
                "session_expiry": data.get("session_expiry"),
                "username": username,
            }

        await deactivate_active_sessions(session, client_id)
        await insert_active_session(session, client_id, snapshot)

    run_async(lambda: run_in_session(work))


def persist_refresh_session(args: tuple[Any, ...], kwargs: dict[str, Any], result: dict[str, Any]) -> None:
    if not result.get("success"):
        return

    data = as_dict(result.get("data"))

    async def work(session) -> None:
        gstin = sentinel(kwargs.get("gstin") or (args[0] if args else ""))
        if not gstin:
            return

        snapshot = current_session_snapshot(gstin)
        if not snapshot and data:
            snapshot = {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "token_expiry": data.get("token_expiry"),
                "session_expiry": data.get("session_expiry"),
            }

        client_id = await ensure_client(session, gstin, snapshot.get("username"))
        updated = await update_active_session(session, client_id, snapshot)
        if not updated:
            await insert_active_session(session, client_id, snapshot)

    run_async(lambda: run_in_session(work))


async def append_or_update_otp_after_verification(
    *,
    session,
    client_id: int,
    success: bool,
    status_cd: str | None,
    message: str | None,
) -> None:
    from .persistence_common import update_latest_otp_request

    await update_latest_otp_request(
        session,
        client_id=client_id,
        status="verified" if success else "failed",
        upstream_status_cd=status_cd,
        message=message,
    )


async def update_active_session(session, client_id: int, snapshot: dict[str, Any]) -> bool:
    active_session_id = (
        await session.execute(
            select(CLIENT_SESSIONS.c.id)
            .where(
                CLIENT_SESSIONS.c.client_id == client_id,
                CLIENT_SESSIONS.c.is_active.is_(True),
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    if active_session_id is None:
        return False

    await session.execute(
        update(CLIENT_SESSIONS)
        .where(CLIENT_SESSIONS.c.id == active_session_id)
        .values(
            access_token=snapshot.get("access_token") or "",
            refresh_token=snapshot.get("refresh_token"),
            token_expiry=to_datetime(snapshot.get("token_expiry")),
            session_expiry=to_datetime(snapshot.get("session_expiry")),
            is_active=True,
        )
    )
    return True


AUTH_PERSISTERS = {
    "generate_otp": persist_generate_otp,
    "verify_otp": persist_verify_otp,
    "refresh_session": persist_refresh_session,
}
