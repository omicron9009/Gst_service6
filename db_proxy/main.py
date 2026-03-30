from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from database.core.database import ensure_database_ready, get_db

from .config import settings
from .security import require_basic_auth
from .service import fetch_business_dataset, fetch_clients


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_database_ready()
    yield


app = FastAPI(title="GST DB Proxy", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/fetch")
async def fetch_all_business_tables(
    gstin: list[str] | None = Query(
        default=None,
        description="Repeat this query param to filter one or more GSTINs.",
    ),
    client_id: list[int] | None = Query(
        default=None,
        description="Repeat this query param to filter one or more client ids.",
    ),
    include_inactive: bool = Query(
        default=settings.default_include_inactive,
        description="Include inactive clients in the result set.",
    ),
    tables: list[str] | None = Query(
        default=None,
        description="Optional subset of business tables to fetch.",
    ),
    _: str = Depends(require_basic_auth),
    db: AsyncSession = Depends(get_db),
):
    return await fetch_business_dataset(
        db,
        gstins=gstin,
        client_ids=client_id,
        include_inactive=include_inactive,
        tables=tables,
    )


@app.get("/clients")
async def list_clients(
    gstin: list[str] | None = Query(
        default=None,
        description="Repeat this query param to filter one or more GSTINs.",
    ),
    client_id: list[int] | None = Query(
        default=None,
        description="Repeat this query param to filter one or more client ids.",
    ),
    include_inactive: bool = Query(
        default=settings.default_include_inactive,
        description="Include inactive clients in the result set.",
    ),
    _: str = Depends(require_basic_auth),
    db: AsyncSession = Depends(get_db),
):
    return await fetch_clients(
        db,
        gstins=gstin,
        client_ids=client_id,
        include_inactive=include_inactive,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("db_proxy.main:app", host=settings.host, port=settings.port, reload=False)
