"""Endpoints for managing runtime settings (API credentials, etc.)."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import config  # noqa: F401  – so we can reload credentials at runtime
from services.auth import invalidate_platform_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])

_CREDS_PATH = Path(__file__).resolve().parent.parent / "sessions" / "api_credentials.json"


class ApiCredentialsIn(BaseModel):
    api_key: str
    api_secret: str


class ApiCredentialsOut(BaseModel):
    has_credentials: bool
    api_key: str
    api_secret: str


def _mask(value: str) -> str:
    """Show first 8 and last 4 chars, mask the middle with **."""
    if len(value) <= 12:
        return value[:4] + "**" + value[-4:] if len(value) > 8 else value
    return value[:8] + "**" + value[-4:]


@router.get("/api-credentials", response_model=ApiCredentialsOut)
def get_api_credentials():
    """Return stored credentials (partially masked) if they exist."""
    try:
        if _CREDS_PATH.exists():
            data = json.loads(_CREDS_PATH.read_text(encoding="utf-8"))
            key = data.get("api_key", "").strip()
            secret = data.get("api_secret", "").strip()
            if key and secret:
                return ApiCredentialsOut(
                    has_credentials=True,
                    api_key=_mask(key),
                    api_secret=_mask(secret),
                )
    except (json.JSONDecodeError, OSError):
        pass

    # Fall back to env-var based credentials
    if config.API_KEY:
        return ApiCredentialsOut(
            has_credentials=True,
            api_key=_mask(config.API_KEY),
            api_secret=_mask(config.API_SECRET),
        )

    return ApiCredentialsOut(has_credentials=False, api_key="", api_secret="")


@router.post("/api-credentials")
def save_api_credentials(body: ApiCredentialsIn):
    """Persist Sandbox API key & secret to sessions/api_credentials.json."""
    key = body.api_key.strip()
    secret = body.api_secret.strip()

    if not key or not secret:
        raise HTTPException(status_code=400, detail="Both api_key and api_secret are required.")

    _CREDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"api_key": key, "api_secret": secret}, indent=2)
    _CREDS_PATH.write_text(payload, encoding="utf-8")

    # Hot-reload into running process
    config.API_KEY = key
    config.API_SECRET = secret
    config.PLATFORM_TOKEN = secret
    invalidate_platform_token()

    logger.info("API credentials updated via settings panel.")
    return {"status": "ok"}
