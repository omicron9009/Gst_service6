# main.py
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# BUG FIX: Import routers from flat module names to match project layout.
# If you later move them into a 'routers/' sub-package, re-add the prefix.
from routers.auth_router import router as auth_router
from routers.gst_r1_router import router as gstr1_router
from routers.gstr_2A_router import router as gstr2a_router
from routers.gstr_2B_router import router as gstr2b_router
from routers.gstr_3B_router import router as gstr3b_router
from routers.gstr_9_router import router as gstr9_router
from routers.ledger_router import router as ledger_router
from routers.gst_return_status_router import router as gst_return_status_router
from routers.reconciliation_router import router as reconciliation_router
from routers.settings_router import router as settings_router
from services.session_refresh_manager import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="GST API Service", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(gstr1_router)
app.include_router(gstr2a_router)
app.include_router(gstr2b_router)
app.include_router(gstr3b_router)
app.include_router(gstr9_router)
app.include_router(ledger_router)
app.include_router(gst_return_status_router)
app.include_router(reconciliation_router)
app.include_router(settings_router)


@app.get("/health")
def health():
    return {"status": "ok"}