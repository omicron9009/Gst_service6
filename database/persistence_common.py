from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from sqlalchemy import UniqueConstraint, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from .core.base import Base
from .core.database import PersistenceSessionLocal
from .models import Client, ClientSession, OtpRequest  # noqa: F401
from .services.gst_return_status import models as _gst_return_status_models  # noqa: F401
from .services.gstr1 import models as _gstr1_models  # noqa: F401
from .services.gstr2a import models as _gstr2a_models  # noqa: F401
from .services.gstr2b import models as _gstr2b_models  # noqa: F401
from .services.gstr3b import models as _gstr3b_models  # noqa: F401
from .services.gstr9 import models as _gstr9_models  # noqa: F401
from .services.ledger import models as _ledger_models  # noqa: F401


logger = logging.getLogger(__name__)

CLIENTS = Base.metadata.tables["clients"]
CLIENT_SESSIONS = Base.metadata.tables["client_sessions"]
OTP_REQUESTS = Base.metadata.tables["otp_requests"]


def normalize_gstin(gstin: str | None) -> str:
    return (gstin or "").strip().upper()


def sentinel(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def result_to_dict(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        return result
    model_dump = getattr(result, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        return dumped if isinstance(dumped, dict) else {}
    return {}


def resolve_username(gstin: str, explicit_username: str | None = None) -> str:
    username = (explicit_username or "").strip()
    if username:
        return username

    try:
        from session_storage import get_session

        session = get_session(gstin)
        if session:
            username = (session.get("username") or "").strip()
            if username:
                return username
    except Exception:
        logger.exception("db_username_resolution_failed gstin=%s", gstin)

    return ""


def to_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1_000_000_000_000:
            ts = ts / 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            ts = float(stripped)
        except ValueError:
            ts = None
        if ts is not None:
            if ts > 1_000_000_000_000:
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        try:
            parsed = datetime.fromisoformat(stripped.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    return None


def to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def run_async(coro_factory: Callable[[], Awaitable[None]]) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is None:
        asyncio.run(coro_factory())
        return

    error: list[Exception] = []

    def runner() -> None:
        try:
            asyncio.run(coro_factory())
        except Exception as exc:  # pragma: no cover
            error.append(exc)

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join()
    if error:
        raise error[0]


async def run_in_session(work: Callable[[AsyncSession], Awaitable[None]]) -> None:
    async with PersistenceSessionLocal() as session:
        await work(session)
        await session.commit()


async def ensure_client(session: AsyncSession, gstin: str, username: str | None = None) -> int:
    gstin = normalize_gstin(gstin)
    if not gstin:
        raise ValueError("GSTIN is required for client persistence.")

    resolved_username = resolve_username(gstin, username)
    stmt = insert(CLIENTS).values(
        gstin=gstin,
        username=resolved_username,
        is_active=True,
    )

    update_values: dict[str, Any] = {
        "is_active": True,
        "updated_at": func.now(),
    }
    if resolved_username:
        update_values["username"] = resolved_username

    stmt = stmt.on_conflict_do_update(
        constraint="uq_clients_gstin",
        set_=update_values,
    ).returning(CLIENTS.c.id)

    result = await session.execute(stmt)
    return int(result.scalar_one())


def unique_constraint_name(table_name: str) -> str:
    table = Base.metadata.tables[table_name]
    for constraint in table.constraints:
        if isinstance(constraint, UniqueConstraint) and constraint.name:
            return constraint.name
    raise ValueError(f"No named unique constraint found for table '{table_name}'.")


async def upsert_row(session: AsyncSession, table_name: str, values: dict[str, Any]) -> None:
    table = Base.metadata.tables[table_name]
    stmt = insert(table).values(**values)

    update_values = {
        key: value
        for key, value in values.items()
        if key not in {"id", "created_at", "fetched_at"}
    }
    if "updated_at" in table.c:
        update_values["updated_at"] = func.now()

    stmt = stmt.on_conflict_do_update(
        constraint=unique_constraint_name(table_name),
        set_=update_values,
    )
    await session.execute(stmt)


async def append_otp_request(
    session: AsyncSession,
    *,
    client_id: int,
    status: str,
    upstream_status_cd: str | None,
    message: str | None,
    expires_at: datetime | None = None,
) -> None:
    await session.execute(
        insert(OTP_REQUESTS).values(
            client_id=client_id,
            status=status,
            upstream_status_cd=upstream_status_cd,
            message=message,
            expires_at=expires_at,
        )
    )


async def update_latest_otp_request(
    session: AsyncSession,
    *,
    client_id: int,
    status: str,
    upstream_status_cd: str | None,
    message: str | None,
) -> None:
    pending_stmt = (
        select(OTP_REQUESTS.c.id)
        .where(OTP_REQUESTS.c.client_id == client_id, OTP_REQUESTS.c.status == "pending")
        .order_by(OTP_REQUESTS.c.created_at.desc())
        .limit(1)
    )
    target_id = (await session.execute(pending_stmt)).scalar_one_or_none()

    if target_id is None:
        latest_stmt = (
            select(OTP_REQUESTS.c.id)
            .where(OTP_REQUESTS.c.client_id == client_id)
            .order_by(OTP_REQUESTS.c.created_at.desc())
            .limit(1)
        )
        target_id = (await session.execute(latest_stmt)).scalar_one_or_none()

    if target_id is None:
        await append_otp_request(
            session,
            client_id=client_id,
            status=status,
            upstream_status_cd=upstream_status_cd,
            message=message,
        )
        return

    await session.execute(
        update(OTP_REQUESTS)
        .where(OTP_REQUESTS.c.id == target_id)
        .values(
            status=status,
            upstream_status_cd=upstream_status_cd,
            message=message,
        )
    )


async def deactivate_active_sessions(session: AsyncSession, client_id: int) -> None:
    await session.execute(
        update(CLIENT_SESSIONS)
        .where(CLIENT_SESSIONS.c.client_id == client_id, CLIENT_SESSIONS.c.is_active.is_(True))
        .values(is_active=False, updated_at=func.now())
    )


async def deactivate_client_session_by_gstin(gstin: str) -> None:
    async with PersistenceSessionLocal() as session:
        row = (
            await session.execute(select(CLIENTS.c.id).where(CLIENTS.c.gstin == gstin))
        ).scalar_one_or_none()
        if row is None:
            await session.commit()
            return
        await deactivate_active_sessions(session, int(row))
        await session.commit()


def current_session_snapshot(gstin: str) -> dict[str, Any]:
    try:
        from session_storage import get_session

        session = get_session(gstin)
        return session if isinstance(session, dict) else {}
    except Exception:
        logger.exception("db_session_snapshot_failed gstin=%s", gstin)
        return {}


async def insert_active_session(session: AsyncSession, client_id: int, snapshot: dict[str, Any]) -> None:
    await session.execute(
        insert(CLIENT_SESSIONS).values(
            client_id=client_id,
            access_token=snapshot.get("access_token") or "",
            refresh_token=snapshot.get("refresh_token"),
            token_expiry=to_datetime(snapshot.get("token_expiry")),
            session_expiry=to_datetime(snapshot.get("session_expiry")),
            is_active=True,
        )
    )


async def records_table_upsert(
    session: AsyncSession,
    *,
    table_name: str,
    gstin: str,
    year: str,
    month: str,
    records: list[Any],
    upstream_status_code: Any = None,
    extra: dict[str, Any] | None = None,
    username: str | None = None,
) -> None:
    client_id = await ensure_client(session, gstin, username)
    values = {
        "client_id": client_id,
        "year": year,
        "month": month,
        "records": records,
        "upstream_status_code": upstream_status_code,
    }
    if extra:
        values.update(extra)
    await upsert_row(session, table_name, values)
