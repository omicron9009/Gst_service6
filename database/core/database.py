from __future__ import annotations

import importlib
import logging
from collections.abc import AsyncGenerator

import asyncpg
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from .base import Base
from .config import settings


logger = logging.getLogger(__name__)


def _build_sessionmaker(target_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=target_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.echo_sql,
    future=True,
    pool_pre_ping=True,
)

persistence_engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.echo_sql,
    future=True,
    # Persistence helpers run inside short-lived asyncio.run() loops from sync service code.
    # NullPool prevents loop-bound asyncpg connections from being reused across those loops.
    poolclass=NullPool,
)

AsyncSessionLocal = _build_sessionmaker(engine)
PersistenceSessionLocal = _build_sessionmaker(persistence_engine)


def _is_postgresql_url(url: URL) -> bool:
    return url.get_backend_name() == "postgresql"


def _quote_postgres_ident(value: str) -> str:
    return f'"{value.replace(chr(34), chr(34) * 2)}"'


def _import_model_packages() -> None:
    for module_name in (
        "database.models",
        "database.services.gstr1",
        "database.services.gstr2a",
        "database.services.gstr2b",
        "database.services.gstr3b",
        "database.services.gstr9",
        "database.services.gst_return_status",
        "database.services.ledger",
    ):
        importlib.import_module(module_name)


async def ensure_database_exists() -> None:
    url = make_url(settings.database_url)
    if not _is_postgresql_url(url):
        return

    database_name = url.database
    if not database_name:
        raise RuntimeError("DATABASE_URL must include a PostgreSQL database name.")

    admin_candidates: list[str] = []
    for candidate in (settings.database_admin_db, "postgres", "template1"):
        if candidate and candidate not in admin_candidates and candidate != database_name:
            admin_candidates.append(candidate)

    last_error: Exception | None = None
    connection: asyncpg.Connection | None = None
    for admin_db in admin_candidates:
        try:
            connection = await asyncpg.connect(
                user=url.username,
                password=url.password,
                host=url.host or "localhost",
                port=int(url.port or 5432),
                database=admin_db,
            )
            break
        except Exception as exc:  # pragma: no cover - exercised only when local PG access fails
            last_error = exc

    if connection is None:
        raise RuntimeError(
            f"Unable to connect to a PostgreSQL admin database ({', '.join(admin_candidates)})."
        ) from last_error

    try:
        exists = await connection.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            database_name,
        )
        if exists:
            return

        await connection.execute(f"CREATE DATABASE {_quote_postgres_ident(database_name)}")
        logger.info("Created PostgreSQL database '%s'.", database_name)
    except asyncpg.exceptions.DuplicateDatabaseError:
        logger.info("PostgreSQL database '%s' was created concurrently.", database_name)
    finally:
        await connection.close()


async def ensure_database_ready() -> None:
    await ensure_database_exists()
    _import_model_packages()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
