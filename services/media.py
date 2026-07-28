import io
import time
import logging
from typing import List, Optional
from PIL import Image
import httpx
from sqlalchemy.orm import Session

# ── Custom exceptions ──
class MediaServiceError(Exception): pass
class InvalidFileNameError(MediaServiceError): pass
class FileNotFoundError(MediaServiceError): pass
class ImageProcessingError(MediaServiceError): pass
class PocketBaseUnreachableError(MediaServiceError): pass

logger = logging.getLogger("MediaService")

# ═══════════════════════════════════════════════════════
#  PocketBase File Client
# ═══════════════════════════════════════════════════════

class PocketBaseFileClient:
    """
    Talks to PocketBase for file storage.
    Strictly in-memory, no local file saving.
    """

    def __init__(self, pb_url: str, admin_email: str, admin_password: str):
        self.pb_url = pb_url.rstrip('/')
        self.admin_email = admin_email
        self.admin_password = admin_password
        self._token: Optional[str] = None
        self._token_expires: float = 0
        self._collection_ensured: bool = False

    async def _get_token(self) -> str:
        now = time.time()
        if self._token and self._token_expires > now + 300:
            return self._token

        if not self.admin_email or not self.admin_password:
            raise PocketBaseUnreachableError("PocketBase admin credentials not configured.")

        try:
            async with httpx.AsyncClient(timeout=10.0) as c:
                payload = {"identity": self.admin_email, "password": self.admin_password}
                
                # 1. Try PB v0.23+ (_superusers collection)
                r = await c.post(f"{self.pb_url}/api/collections/_superusers/auth-with-password", json=payload)
                
                # 2. Fallback for older PB versions (admins)
                if r.status_code == 404:
                    r = await c.post(f"{self.pb_url}/api/admins/auth-with-password", json=payload)

                if r.status_code != 200:
                    raise PocketBaseUnreachableError(f"PocketBase auth failed ({r.status_code}): {r.text}")
                
                data = r.json()
                self._token = data["token"]
                self._token_expires = now + 86_400

                # Auto-ensure the media collection exists on the very first successful auth
                if not self._collection_ensured:
                    await self._ensure_media_collection(c)
                    self._collection_ensured = True

                return self._token

        except httpx.RequestError as e:
            raise PocketBaseUnreachableError(f"Cannot reach PocketBase at {self.pb_url}. Details: {e}")

    async def _ensure_media_collection(self, client: httpx.AsyncClient):
        """Creates the 'media' collection if it doesn't exist."""
        r = await client.get(
            f"{self.pb_url}/api/collections",
            headers={"Authorization": f"Bearer {self._token}"}
        )
        if r.status_code == 200:
            existing = [col["name"] for col in r.json().get("items", [])]
            if "media" in existing:
                return  # Already exists

        body = {
            "name": "media",
            "type": "base",
            "fields": [
                {"name": "filename",      "type": "text",     "required": True},
                {"name": "original_name", "type": "text",     "required": False},
                {"name": "friendly_name", "type": "text",     "required": False},
                {"name": "description",   "type": "text",     "required": False},
                {"name": "size",          "type": "number",   "required": False},
                {"name": "format",        "type": "text",     "required": False},
                {"name": "file",          "type": "file",     "required": False, "options": {"maxSelect": 1, "maxSize": 20971520}},
                
                # --- Updated Autodate Fields ---
                {
                    "name": "created",       
                    "type": "autodate",     
                    "options": {
                        "onCreate": True,
                        "onUpdate": False
                    }
                },
                {
                    "name": "updated",       
                    "type": "autodate",     
                    "options": {
                        "onCreate": True,
                        "onUpdate": True
                    }
                },
            ],
        }
        await client.post(
            f"{self.pb_url}/api/collections",
            headers={"Authorization": f"Bearer {self._token}"},
            json=body,
        )
        logger.info("📦 Created 'media' collection in PocketBase")

    async def upload(self, file_bytes: bytes, filename: str, original_name: str, file_size: int, file_format: str) -> dict:
        token = await self._get_token()

        try:
            async with httpx.AsyncClient(timeout=30.0) as c:
                # Send raw bytes directly to PocketBase
                files = {"file": (filename, file_bytes, f"image/{file_format}")}
                data = {
                    "filename": filename,
                    "original_name": original_name,
                    "size": str(file_size),
                    "format": file_format,
                }
                r = await c.post(
                    f"{self.pb_url}/api/collections/media/records",
                    headers={"Authorization": f"Bearer {token}"},
                    data=data,
                    files=files,
                )

                if r.status_code not in (200, 201):
                    raise MediaServiceError(f"PocketBase upload failed: {r.text[:200]}")

                record = r.json()
                cid = record.get("collectionId", "")
                stored = record.get("file", "")
                
                return {
                    "record_id": record["id"],
                    "url": f"{self.pb_url}/api/files/{cid}/{record['id']}/{stored}",
                    "filename": filename,
                }
        except httpx.RequestError as e:
            raise PocketBaseUnreachableError(f"Connection failed: {e}")

    async def list_files(self) -> List[dict]:
        token = await self._get_token()
        try:
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.get(
                    f"{self.pb_url}/api/collections/media/records",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"perPage": 500, "sort":"-created"},
                )
                if r.status_code != 200:
                    raise MediaServiceError(f"Failed to list files: {r.text[:200]}")

                result = []
                for item in r.json().get("items", []):
                    stored = item.get("file", "")
                    cid = item.get("collectionId", "")
                    result.append({
                        "id": item["id"],
                        "filename": item.get("filename", stored),
                        "original_name": item.get("original_name", ""),
                        "friendly_name": item.get("friendly_name", ""),
                        "description": item.get("description", ""),
                        "url": f"{self.pb_url}/api/files/{cid}/{item['id']}/{stored}",
                        "size": item.get("size", 0),
                        "format": item.get("format", ""),
                        "created": item.get("created", ""),
                    })
                return result
        except httpx.RequestError as e:
            raise PocketBaseUnreachableError(f"Connection failed: {e}")

    async def delete(self, record_id: str):
        token = await self._get_token()
        try:
            async with httpx.AsyncClient(timeout=10.0) as c:
                await c.delete(
                    f"{self.pb_url}/api/collections/media/records/{record_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
        except httpx.RequestError as e:
            logger.error(f"PB unreachable during delete of {record_id}: {e}")

    async def patch_metadata(self, record_id: str, updates: dict):
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=10.0) as c:
            await c.patch(
                f"{self.pb_url}/api/collections/media/records/{record_id}",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=updates
            )


# ═══════════════════════════════════════════════════════
#  MediaService — Strictly PocketBase
# ═══════════════════════════════════════════════════════

class MediaService:
    def __init__(self):
        self._pb_client: Optional[PocketBaseFileClient] = None
        self._pb_error: Optional[str] = "PocketBase is not configured."
        self.MEDIA_DIR = "uploads/media"

    def configure_pocketbase(self, pb_url: str, admin_email: str, admin_password: str):
        """Synchronously apply config; connection tested lazily on first API call."""
        if pb_url and admin_email and admin_password:
            self._pb_client = PocketBaseFileClient(pb_url, admin_email, admin_password)
            self._pb_error = None
            logger.info(f"MediaService configured for PocketBase at {pb_url}")
        else:
            self._pb_client = None
            self._pb_error = "Missing PocketBase credentials."

    async def list_files(self) -> List[dict]:
        if not self._pb_client:
            raise MediaServiceError(self._pb_error)
        return await self._pb_client.list_files()

    async def delete_file(self, record_id: str):
        if not self._pb_client:
            raise MediaServiceError(self._pb_error)
        await self._pb_client.delete(record_id)

    async def patch_file(self, record_id: str, updates: dict):
        if not self._pb_client:
            raise MediaServiceError(self._pb_error)
        await self._pb_client.patch_metadata(record_id, updates)

    async def process_and_save_image(self, file_contents: bytes, original_filename: str) -> dict:
        """
        Process an uploaded image entirely in RAM, then push to PocketBase.
        """
        if not self._pb_client:
            raise MediaServiceError("Cannot upload: " + self._pb_error)

        try:
            # Load into memory
            image = Image.open(io.BytesIO(file_contents))
            has_alpha = image.mode in ('RGBA', 'P', 'LA') or (image.mode == 'P' and 'transparency' in image.info)
            
            # Setup output buffer
            output_io = io.BytesIO()
            import os
            original_name = os.path.splitext(original_filename)[0]
            timestamp = int(time.time())

            # Convert & Compress directly into RAM
            if has_alpha:
                webp_image = image.convert('RGBA')
                webp_image.save(output_io, 'WEBP', quality=80, method=4)
                best_format = 'webp'
            else:
                image.convert('RGB').save(output_io, 'JPEG', quality=80, optimize=True)
                best_format = 'jpg'

            # Extract bytes from RAM buffer
            file_bytes = output_io.getvalue()
            best_size = len(file_bytes)
            final_filename = f"{original_name}_{timestamp}.{best_format}"

            # Upload directly to PB
            result = await self._pb_client.upload(
                file_bytes=file_bytes,
                filename=final_filename,
                original_name=original_filename,
                file_size=best_size,
                file_format=best_format,
            )

            return {
                "original": original_filename,
                "saved_as": final_filename,
                "url": result["url"],
                "size": best_size,
                "format_chosen": best_format,
                "storage": "pocketbase",
                "record_id": result["record_id"]
            }

        except PocketBaseUnreachableError as e:
            raise MediaServiceError(f"Upload failed - PocketBase Unreachable: {e}")
        except Exception as e:
            raise ImageProcessingError(f"Failed to process image: {e}")


# ═══════════════════════════════════════════════════════
#  Helper: build MediaService from ConfigService
# ═══════════════════════════════════════════════════════

def configure_media_from_db(db: Session, media_service: MediaService):
    from services.config import ConfigService
    settings = ConfigService(db).get_all_settings()

    media_service.configure_pocketbase(
        pb_url=settings.get("pb_url", "").strip(),
        admin_email=settings.get("pb_admin_email", "").strip(),
        admin_password=settings.get("pb_admin_password", "").strip()
    )
    return {"configured": media_service._pb_client is not None, "error": media_service._pb_error}