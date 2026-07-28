# file: routes/admin_route.py

import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from data.database import get_db
from data.schemas import CurrentUser
from routes.public_route import render_db_template
from services.pages import PageService
from services.users import UserService
from src.dependencies import optional_user
from src import dependencies as dep

router = APIRouter(tags=["Anita"])
ADMIN_DIR = "static/anita"


def get_page_service(db: Session = Depends(get_db)) -> PageService:
    return PageService(db)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


def render_admin_page(view_slug: str) -> HTMLResponse:
    """
    Reads the shell HTML, injects the view content server-side,
    and returns a complete page. No HTMX, no partials, no client-side routing.
    Just a full HTML page every time.
    """
    shell_path = os.path.join(ADMIN_DIR, "index.html")
    view_path = os.path.join(ADMIN_DIR, "views", f"{view_slug}.html")

    if not os.path.exists(shell_path):
        return HTMLResponse("Shell not found", status_code=500)

    with open(shell_path, "r", encoding="utf-8") as f:
        shell = f.read()

    if os.path.exists(view_path):
        with open(view_path, "r", encoding="utf-8") as f:
            view_content = f.read()
    else:
        view_content = f'<div class="p-6 text-gray-500">View "{view_slug}" not found.</div>'

    # Replace placeholder with view content
    html = shell.replace("<!-- VIEW_CONTENT -->", view_content)
    html = html.replace("<!-- ACTIVE_TAB -->", view_slug)

    return HTMLResponse(html)


@router.get("/anita")
async def admin_root():
    return RedirectResponse("/anita/dashboard")


@router.get("/anita/{slug}")
async def admin_page(
    slug: str,
    request: Request,
    user_service: UserService = Depends(get_user_service),
    user: Optional[CurrentUser] = Depends(dep.optional_user),
):
    # Auth gate
    if not user:
        return RedirectResponse(url="/auth", status_code=302)

    valid_views = {"dashboard", "page", "structure", "users", "media", "config"}

    if slug in valid_views:
        return render_admin_page(slug)

    raise HTTPException(status_code=404, detail="Content not available")


@router.get("/anita/preview/{slug}", response_class=HTMLResponse)
def serve_any_post(
    slug: str,
    page_service: PageService = Depends(get_page_service),
    user_service: UserService = Depends(get_user_service),
    user: Optional[CurrentUser] = Depends(dep.optional_user),
):
    if not user:
        return RedirectResponse(url="/auth", status_code=302)

    page = page_service.get_page_by_slug(slug)

    if page.type == "html":
        return HTMLResponse(content=page.html, status_code=200)

    markdown_template = page_service.get_first_page_by_labels(["sys:template", "any:read"])
    if not markdown_template:
        raise HTTPException(status_code=500, detail="System Error: Markdown template missing.")

    context = {
        "title": page.title,
        "markdown_content": page.markdown,
        "author": page.author if hasattr(page, "author") else "Unknown",
        "published": page.created if hasattr(page, "created_at") else "",
        "updated": page.updated if hasattr(page, "updated_at") else "",
        "description": page.content if hasattr(page, "description") else "",
        "thumb": page.thumb if hasattr(page, "thumbnail") else "",
    }

    rendered_html = render_db_template(markdown_template.html, context)
    return HTMLResponse(content=rendered_html, status_code=200)
