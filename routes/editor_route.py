import os
import re  # <--- Import the regex module
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from src.dependencies import get_current_user

router = APIRouter(tags=["Asta Markdown Editor"])

# --- CONFIG ---
RAW_INDEX_PATH = "static/raw/index.html"
AINA_INDEX_PATH = "static/aina/index.html"

# --- HELPER ---
def render_template(file_path: str, context: dict = None):
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Editor template not found")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if context:
        for key, value in context.items():
            pattern = re.compile(r"{{\s*" + re.escape(key) + r"\s*}}")
            content = pattern.sub(str(value), content)

    return HTMLResponse(content)

# --- ROUTES ---

@router.get("/editor/raw/{slug}", response_class=HTMLResponse)
async def raw_editor_view(
    slug: str, 
    request: Request, 
    user: Optional[dict] = Depends(get_current_user)
):
    """
    Serves the Single Page Application for the Editor.
    """
    if not user:
        return RedirectResponse(url=f"/auth/login?next=/asta/editor/{slug}", status_code=302)

    # This will now correctly inject the slug
    return render_template(RAW_INDEX_PATH, {"slug": slug})

@router.get("/editor/aina/{slug}", response_class=HTMLResponse)
async def aina_editor_view(
    slug: str, 
    request: Request, 
    user: Optional[dict] = Depends(get_current_user)
):
    """
    Serves the Single Page Application for the Editor.
    """
    if not user:
        return RedirectResponse(url=f"/auth/login?next=/anita/", status_code=302)

    # This will now correctly inject the slug
    return render_template(AINA_INDEX_PATH, {"slug": slug})