"""Auth API routes: login, logout, session check."""

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from ..auth import (
    verify_password,
    create_session,
    validate_session,
    delete_session,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_COOKIE = "sp_session"
COOKIE_MAX_AGE = 8 * 3600  # match SESSION_TIMEOUT


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response):
    user = verify_password(body.username, body.password)
    if not user:
        return {"ok": False, "error": "Invalid username or password"}

    token = create_session(user, request)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=COOKIE_MAX_AGE,
        path="/",
    )
    return {
        "ok": True,
        "user": {
            "username": user["username"],
            "display_name": user["display_name"],
            "role": user["role"],
        },
    }


@router.post("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        delete_session(token)
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    user = validate_session(token) if token else None
    if not user:
        return {"authenticated": False}
    return {"authenticated": True, "user": user}
