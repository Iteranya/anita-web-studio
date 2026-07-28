# file: api/admin.py (or wherever this lives in your routes)

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from data.database import get_db
from services.config import ConfigService
from src.dependencies import require_admin

router = APIRouter(prefix="/config", tags=["Config"])

# ──────────────────────────────────────────────────
# SystemConfiguration — Extended with PB + Midtrans
# ──────────────────────────────────────────────────

class SystemConfiguration(BaseModel):
    # ── AI / General ──
    system_note: str = "You are a friendly AI Assistant."
    ai_endpoint: str = ""
    base_llm: str = ""
    temperature: float = 0.7
    ai_key: Optional[str] = ""
    theme: Optional[str] = "default"
    routes: Optional[List[Dict[str, Any]]] = []

    # ── PocketBase ──
    pb_url: str = Field(
        default="http://localhost:8090",
        description="PocketBase instance URL (e.g. https://db.artesparadox.net/)"
    )
    pb_admin_email: str = Field(
        default="",
        description="PocketBase superuser email for admin API access"
    )
    pb_admin_password: str = Field(
        default="",
        description="PocketBase superuser password (stored as-is; use HTTPS)"
    )

    # ── Midtrans ──
    midtrans_server_key: str = Field(
        default="",
        description="Midtrans server key (starts with 'SB-Mid-server-' for sandbox)"
    )
    midtrans_merchant_id: str = Field(
        default="",
        description="Midtrans merchant ID"
    )
    midtrans_is_production: bool = Field(
        default=False,
        description="False = Sandbox, True = Production"
    )
    midtrans_notification_url: str = Field(
        default="",
        description="Override URL for Midtrans payment notifications."
    )
    # ── NEW: Configurable payment pipeline fields ──
    midtrans_order_prefix: str = Field(
        default="ORD-",
        description="Prefix for order IDs (e.g. 'ORD-', 'ACCA-', 'WDY-')"
    )
    midtrans_user_collection: str = Field(
        default="users",
        description="PocketBase collection name for end-users"
    )
    midtrans_transaction_collection: str = Field(
        default="transactions",
        description="PocketBase collection name for transaction ledger"
    )
    midtrans_registration_collection: str = Field(
        default="registrations",
        description="PocketBase collection name for registration links"
    )

    class Config:
        from_attributes = True



@router.get("/", response_model=SystemConfiguration)
def get_config(
    user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Load all system settings from the database with sensible defaults."""
    service = ConfigService(db)
    service.seed_initial_settings()
    settings = service.get_all_settings()
    return settings


@router.post("/", response_model=SystemConfiguration)
def update_config(
    updated: SystemConfiguration,
    user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    service = ConfigService(db)
    settings_data = updated.model_dump()

    # Never overwrite secrets with empty strings
    if not settings_data.get("pb_admin_password", "").strip():
        del settings_data["pb_admin_password"]
    if not settings_data.get("ai_key", "").strip():
        del settings_data["ai_key"]

    saved_settings = service.save_settings(settings_data)
    return saved_settings
