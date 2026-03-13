from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from arxi.auth.middleware import get_current_user
from arxi.auth.models import User
from arxi.auth.schemas import ChangePasswordRequest, LoginRequest, UserResponse
from arxi.auth.service import AuthService
from arxi.config import settings
from arxi.database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _create_token(user: User) -> str:
    payload = {
        "sub": user.username,
        "role": user.role.value,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@router.post("/login", response_model=UserResponse)
async def login(req: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    user = await svc.authenticate(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = _create_token(user)
    response.set_cookie(
        key="arxi_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
        max_age=settings.jwt_expiry_hours * 3600,
    )
    return UserResponse(
        id=user.id, username=user.username,
        full_name=user.full_name, role=user.role.value,
    )


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="arxi_token", path="/")
    return {"status": "ok"}


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id, username=user.username,
        full_name=user.full_name, role=user.role.value,
    )


@router.get("/token")
async def get_token(user: User = Depends(get_current_user)):
    """Return a JWT for WebSocket authentication (browsers can't send cookies on WS upgrade)."""
    token = _create_token(user)
    return {"token": token}


@router.put("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = AuthService(db)
    ok = await svc.change_password(user, req.old_password, req.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid current password")
    return {"status": "ok"}
