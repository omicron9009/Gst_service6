# routers/auth_router.py
from fastapi import APIRouter
from pydantic import BaseModel

from services.auth import generate_otp, verify_otp, refresh_session
from session_storage import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


class OTPGenerate(BaseModel):
    username: str
    gstin: str


class OTPVerify(BaseModel):
    username: str
    gstin: str
    otp: str


class RefreshRequest(BaseModel):
    gstin: str


@router.post("/generate-otp")
def generate_otp_route(body: OTPGenerate):
    return generate_otp(body.username, body.gstin)


@router.post("/verify-otp")
def verify_otp_route(body: OTPVerify):
    return verify_otp(body.username, body.gstin, body.otp)


@router.post("/refresh")
def refresh_session_route(body: RefreshRequest):
    return refresh_session(body.gstin)


@router.get("/session/{gstin}")
def get_session_status(gstin: str):
    session = get_session(gstin)
    if not session:
        return {"active": False, "message": "No session found for this GSTIN."}
    return {
        "active": bool(session.get("access_token")),
        "username": session.get("username"),
        "token_expiry": session.get("token_expiry"),
        "session_expiry": session.get("session_expiry"),
        "last_refresh": session.get("last_refresh"),
    }
