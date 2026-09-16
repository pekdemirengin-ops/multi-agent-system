"""Auth endpoint'leri - register, login, me."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.schemas import (
    AuthStatus,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserInfo,
)
from core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_user_from_token,
    user_store,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Token'dan mevcut kullaniciyi alir. Yoksa 401."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token gerekli",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    username = get_user_from_token(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gecersiz veya suresi dolmus token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user_store.exists(username):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanici bulunamadi",
        )
    return username


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str | None:
    """Token varsa kullaniciyi doner, yoksa None."""
    if not credentials:
        return None
    return get_user_from_token(credentials.credentials)


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest) -> TokenResponse:
    """Yeni kullanici kaydi."""
    if user_store.exists(req.username):
        raise HTTPException(status_code=400, detail="Kullanici zaten var")

    if not user_store.create_user(req.username, req.password):
        raise HTTPException(status_code=500, detail="Kayit basarisiz")

    token = create_access_token({"sub": req.username})
    return TokenResponse(
        access_token=token,
        username=req.username,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    """Kullanici girisi."""
    if not user_store.authenticate(req.username, req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanici adi veya sifre yanlis",
        )

    token = create_access_token({"sub": req.username})
    return TokenResponse(
        access_token=token,
        username=req.username,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserInfo)
async def me(username: str = Depends(get_current_user)) -> UserInfo:
    """Mevcut kullanici bilgisi."""
    return UserInfo(username=username, is_admin=(username == "admin"))


@router.get("/status", response_model=AuthStatus)
async def auth_status(
    username: str | None = Depends(get_optional_user),
) -> AuthStatus:
    """Token durumu (opsiyonel)."""
    if username:
        return AuthStatus(authenticated=True, username=username)
    return AuthStatus(authenticated=False)