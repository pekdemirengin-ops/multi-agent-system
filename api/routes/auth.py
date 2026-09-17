"""Auth endpoint'leri - register, login, me, admin."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.schemas import (
    AuthStatus,
    LoginRequest,
    RegisterRequest,
    RoleUpdateRequest,
    TokenResponse,
    UserInfo,
    UserListResponse,
)
from core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_user_from_token,
)
from core.user_store import get_user_store

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


async def get_current_user(
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
    store = await get_user_store()
    user = await store.get_user(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanici bulunamadi",
        )
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kullanici pasif durumda",
        )
    return username


async def get_current_user_info(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """Token'dan mevcut kullanici bilgisini (role dahil) alir."""
    username = await get_current_user(credentials)
    store = await get_user_store()
    user = await store.get_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="Kullanici bulunamadi")
    return {
        "username": user["username"],
        "role": user["role"],
        "created_at": user["created_at"],
        "is_active": user["is_active"],
    }


async def require_admin(
    user_info: dict = Depends(get_current_user_info),
) -> dict:
    """Sadece admin erisebilir."""
    if user_info.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu islem icin admin yetkisi gerekli",
        )
    return user_info


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str | None:
    """Token varsa kullaniciyi doner, yoksa None."""
    if not credentials:
        return None
    return get_user_from_token(credentials.credentials)


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest) -> TokenResponse:
    """Yeni kullanici kaydi (role: user)."""
    store = await get_user_store()
    if await store.exists(req.username):
        raise HTTPException(status_code=400, detail="Kullanici zaten var")

    if not await store.create_user(req.username, req.password, role="user"):
        raise HTTPException(status_code=500, detail="Kayit basarisiz")

    token = create_access_token({"sub": req.username, "role": "user"})
    return TokenResponse(
        access_token=token,
        username=req.username,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest) -> TokenResponse:
    """Kullanici girisi."""
    store = await get_user_store()
    if not await store.authenticate(req.username, req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanici adi veya sifre yanlis",
        )

    user = await store.get_user(req.username)
    role = user["role"] if user else "user"

    token = create_access_token({"sub": req.username, "role": role})
    return TokenResponse(
        access_token=token,
        username=req.username,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserInfo)
async def me(user_info: dict = Depends(get_current_user_info)) -> UserInfo:
    """Mevcut kullanici bilgisi."""
    return UserInfo(
        username=user_info["username"],
        is_admin=(user_info["role"] == "admin"),
        role=user_info["role"],
        created_at=user_info.get("created_at", ""),
    )


@router.get("/status", response_model=AuthStatus)
async def auth_status(
    username: str | None = Depends(get_optional_user),
) -> AuthStatus:
    """Token durumu (opsiyonel)."""
    if username:
        return AuthStatus(authenticated=True, username=username)
    return AuthStatus(authenticated=False)


# ============================================================
# Admin endpoint'leri
# ============================================================

@router.get("/users", response_model=UserListResponse)
async def list_users(
    _admin: dict = Depends(require_admin),
) -> UserListResponse:
    """Tum kullanicilari listeler (sadece admin)."""
    store = await get_user_store()
    users = await store.list_users()
    return UserListResponse(
        users=[UserInfo(
            username=u["username"],
            is_admin=(u["role"] == "admin"),
            role=u["role"],
            created_at=u.get("created_at", ""),
        ) for u in users],
        total=len(users),
    )


@router.delete("/users/{username}")
async def delete_user(
    username: str,
    _admin: dict = Depends(require_admin),
) -> dict:
    """Kullanici siler (sadece admin, admin silinemez)."""
    if username == "admin":
        raise HTTPException(status_code=400, detail="admin silinemez")
    store = await get_user_store()
    if not await store.delete_user(username):
        raise HTTPException(status_code=404, detail="Kullanici bulunamadi")
    return {"ok": True, "deleted": username}


@router.patch("/users/{username}/role")
async def update_role(
    username: str,
    req: RoleUpdateRequest,
    _admin: dict = Depends(require_admin),
) -> dict:
    """Kullanici rolunu gunceller (sadece admin)."""
    if req.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Gecersiz rol")
    if username == "admin" and req.role != "admin":
        raise HTTPException(status_code=400, detail="admin rolu degistirilemez")
    store = await get_user_store()
    if not await store.update_role(username, req.role):
        raise HTTPException(status_code=404, detail="Kullanici bulunamadi")
    return {"ok": True, "username": username, "role": req.role}