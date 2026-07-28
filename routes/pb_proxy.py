import time
import httpx
from fastapi import APIRouter, Request, HTTPException, Depends, status
from fastapi.responses import Response
from typing import Optional
from sqlalchemy.orm import Session

from src.dependencies import optional_user
from data.schemas import CurrentUser
from services.users import UserService
from services.config import ConfigService
from data.database import get_db

router = APIRouter(prefix="/api/pb", tags=["PocketBase Proxy"])

# ── Headers to strip from forwarded requests ──
FORBIDDEN_HEADERS = {
    "host",
    "content-length",
    "transfer-encoding",
    "connection",
    "authorization",
    "cookie",
}

# ── JWT Token Cache ──
_token_cache = {
    "token": None,
    "expires_at": 0,
}


# ======================== DEPENDENCIES ========================

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


def get_config_service(db: Session = Depends(get_db)) -> ConfigService:
    return ConfigService(db)


def require_admin(
    user: Optional[CurrentUser] = Depends(optional_user),
    user_service: UserService = Depends(get_user_service),
):
    """Reject if not logged in OR not an admin/superuser."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required",
        )

    permissions = user_service.get_user_permissions(user.username)

    is_admin = (
        user.role == "admin"
        or "*" in permissions
        or "pb:access" in permissions
    )

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return user


# ======================== PB CONFIG HELPER ========================

def _get_pb_config(db: Session):
    """Read PocketBase settings from the CMS config stored in SQLite."""
    config_service = ConfigService(db)
    settings = config_service.get_all_settings()

    pb_url = settings.get("pb_url", "").strip()
    pb_email = settings.get("pb_admin_email", "").strip()
    pb_password = settings.get("pb_admin_password", "").strip()

    if not pb_url:
        raise HTTPException(
            status_code=500,
            detail="PocketBase URL not configured. Set 'pb_url' in admin config.",
        )

    if not pb_email or not pb_password:
        raise HTTPException(
            status_code=500,
            detail="PocketBase admin credentials not configured. Set 'pb_admin_email' and 'pb_admin_password' in admin config.",
        )

    return pb_url, pb_email, pb_password


# ======================== TOKEN MANAGEMENT ========================

async def get_admin_token(db: Session) -> str:
    """
    Authenticate with PocketBase superuser using credentials from CMS config.
    Caches the token for 24 hours.
    """
    now = time.time()

    # Return cached token if still valid (300s buffer)
    if _token_cache["token"] and _token_cache["expires_at"] > now + 300:
        return _token_cache["token"]

    pb_url, pb_email, pb_password = _get_pb_config(db)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{pb_url}/api/collections/_superusers/auth-with-password",
                json={
                    "identity": pb_email,
                    "password": pb_password,
                },
            )

            if resp.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"PocketBase auth failed ({resp.status_code}): {resp.text[:300]}",
                )

            data = resp.json()
            _token_cache["token"] = data["token"]
            _token_cache["expires_at"] = now + 86400  # 24 hours

            print(f"[PB-PROXY] Authenticated as PocketBase superuser")
            return _token_cache["token"]

        except httpx.RequestError as e:
            raise HTTPException(
                status_code=502,
                detail=f"PocketBase unreachable: {e}",
            )


# ======================== THE PROXY ========================

@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def pocketbase_proxy(
    request: Request,
    path: str,
    admin: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    🔐 Admin-only universal PocketBase proxy.

    Reads PocketBase URL + credentials from the CMS config (SQLite settings),
    NOT from environment variables.

    Frontend calls:
      GET    /api/pb/collections/prestasi_publik/records?page=1&perPage=30
      POST   /api/pb/collections/prestasi_publik/records
      PATCH  /api/pb/collections/prestasi_publik/records/{id}
      DELETE /api/pb/collections/prestasi_publik/records/{id}
    """

    pb_url, _, _ = _get_pb_config(db)
    target_url = f"{pb_url}/api/{path}"

    # Gather headers to forward (strip internal ones)
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in FORBIDDEN_HEADERS
    }

    # Authenticate as PocketBase superuser
    admin_token = await get_admin_token(db)
    headers["Authorization"] = f"Bearer {admin_token}"

    body = await request.body()

    # Forward the request
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.request(
                method=request.method,
                url=target_url,
                params=dict(request.query_params),
                headers=headers,
                content=body,
            )
        except httpx.RequestError as e:
            print(f"[PB-PROXY] {admin.username} | {request.method} /api/{path} → 502 | {e}")
            raise HTTPException(
                status_code=502,
                detail=f"PocketBase unreachable: {e}",
            )

    print(f"[PB-PROXY] {admin.username} | {request.method} /api/{path} → {resp.status_code}")

    response_headers = {
        k: v
        for k, v in resp.headers.items()
        if k.lower() not in (
            "content-encoding",
            "transfer-encoding",
            "content-length",
            "server",
        )
    }

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=response_headers,
    )
