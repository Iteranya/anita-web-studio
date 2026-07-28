# file: routes/media_route.py

import os
from typing import List
from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from data.database import get_db
from services.users import UserService
from src.dependencies import get_current_user
from data.schemas import CurrentUser

from services.media import (
    MediaService,
    configure_media_from_db,
    InvalidFileNameError,
    FileNotFoundError,
    ImageProcessingError,
    PocketBaseUnreachableError,
)

router = APIRouter(prefix="/media", tags=["Media"])
media_service = MediaService()


# ═══ DEPENDENCIES ═══

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


def get_media_service(db: Session = Depends(get_db)) -> MediaService:
    """Configure MediaService with latest PocketBase settings from DB."""
    configure_media_from_db(db, media_service)
    return media_service


# ═══ ROUTES ═══

@router.get("/")
async def list_images(
    user: CurrentUser = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    media_svc: MediaService = Depends(get_media_service),
):
    """List all available media files."""
    user_permissions = user_service.get_user_permissions(user.username)
    if "*" not in user_permissions and "media:read" not in user_permissions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return await media_svc.list_files()

@router.get("/{filename}")
async def get_media(
    filename: str,
    media_svc: MediaService = Depends(get_media_service),
):
    """Serve or redirect to a media file."""
    
    local_path = os.path.join(media_svc.MEDIA_DIR, filename)
    
    # 1. LOCAL CHECK
    if os.path.exists(local_path) and os.path.isfile(local_path):
        # FIX: Do not redirect! Serve the actual file directly from your hard drive.
        return FileResponse(local_path)

    # 2. REMOTE POCKETBASE CHECK
    try:
        if media_svc._pb_client:
            remote_files = await media_svc._pb_client.list_files()
            for img in remote_files:
                if img.get("filename") == filename:
                    return RedirectResponse(url=img["url"], status_code=302)
    except Exception:
        pass

    # 3. NOT FOUND
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"File '{filename}' not found.",
    )


@router.post("/")
async def upload_media(
    files: List[UploadFile] = File(...),
    user: CurrentUser = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    media_svc: MediaService = Depends(get_media_service),
):
    """Upload one or more files."""
    user_permissions = user_service.get_user_permissions(user.username)
    if "*" not in user_permissions and "media:create" not in user_permissions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    reports = []

    for file in files:
        report_data = {"original": file.filename}
        try:
            contents = await file.read()
            if not contents:
                raise ValueError("Uploaded file is empty.")

            processed_data = await media_svc.process_and_save_image(contents, file.filename)
            report_data.update(processed_data)

        except (ImageProcessingError, ValueError) as e:
            report_data["error"] = str(e)
        except PocketBaseUnreachableError as e:
            report_data["error"] = str(e)
        except Exception as e:
            report_data["error"] = f"Unexpected: {e}"

        reports.append(report_data)

    return {"status": "completed", "total": len(files), "files": reports}


@router.delete("/{identifier}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    identifier: str,
    user: CurrentUser = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    media_svc: MediaService = Depends(get_media_service),
):
    """Delete a media file by record ID."""
    user_permissions = user_service.get_user_permissions(user.username)
    if "*" not in user_permissions and "media:delete" not in user_permissions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    try:
        await media_svc.delete_file(identifier)
    except InvalidFileNameError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{record_id}")
async def update_media_metadata(
    record_id: str,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    media_svc: MediaService = Depends(get_media_service),
):
    """Update metadata on a media record."""
    user_permissions = user_service.get_user_permissions(user.username)
    if "*" not in user_permissions and "media:update" not in user_permissions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    if media_svc._pb_client is None:
        raise HTTPException(503, "PocketBase not configured")

    body = await request.json()
    patch_data = {}
    if "friendly_name" in body:
        patch_data["friendly_name"] = body["friendly_name"]
    if "description" in body:
        patch_data["description"] = body["description"]

    if not patch_data:
        raise HTTPException(400, "Nothing to update")

    await media_svc.patch_file(record_id, patch_data)
    return {"status": "ok"}
