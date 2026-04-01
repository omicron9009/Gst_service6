from __future__ import annotations

from fastapi import Depends, FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from database.core.database import get_db

from .config import settings
from .security import require_basic_auth
from .service import (
    fetch_business_dataset,
    fetch_available_periods,
    fetch_clients,
    build_monthly_report_html,
)


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


@app.get("/clients")
async def list_clients(
    gstin: list[str] | None = Query(
        default=None,
        description="Repeat this query param to filter one or more GSTINs.",
    ),
    include_inactive: bool = Query(
        default=settings.default_include_inactive,
        description="Include inactive clients in the result set.",
    ),
    _: str = Depends(require_basic_auth),
    db: AsyncSession = Depends(get_db),
):
    clients = await fetch_clients(
        db,
        gstins=gstin,
        client_ids=None,
        include_inactive=include_inactive,
    )
    return {"clients": clients}


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


@app.get("/report", response_class=HTMLResponse)
async def generate_monthly_report(
    gstin: str = Query(..., description="GSTIN for the report."),
    year: str = Query(..., description="Report year (e.g., '2026')."),
    month: str = Query(..., description="Report month (e.g., '01')."),
    tables: list[str] | None = Query(
        default=None,
        description="Optional subset of tables to include (GSTR-9 tables are excluded).",
    ),
    _: str = Depends(require_basic_auth),
    db: AsyncSession = Depends(get_db),
):
    html = await build_monthly_report_html(
        db,
        gstin=gstin,
        year=year,
        month=month,
        tables=tables,
    )

    filename = f"{gstin}_{year}-{month}_report.html"
    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("db_proxy.main:app", host=settings.host, port=settings.port, reload=False)
