from __future__ import annotations

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from database.core.database import get_db

from .config import settings
from .security import require_basic_auth
from .service import fetch_business_dataset, fetch_available_periods


app = FastAPI(title="GST DB Proxy", version="1.0.0")

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
    year: str | None = Query(
        default=None,
        description="Filter by year (e.g., '2026') - applies to monthly tables only.",
    ),
    month: str | None = Query(
        default=None,
        description="Filter by month (e.g., '01') - applies to monthly tables only.",
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
        year=year,
        month=month,
    )


@app.get("/available-periods")
async def get_available_periods(
    gstin: list[str] | None = Query(
        default=None,
        description="Repeat this query param to filter one or more GSTINs.",
    ),
    _: str = Depends(require_basic_auth),
    db: AsyncSession = Depends(get_db),
):
    return await fetch_available_periods(db, gstins=gstin)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("db_proxy.main:app", host=settings.host, port=settings.port, reload=False)
