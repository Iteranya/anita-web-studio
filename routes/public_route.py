import json
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from jinja2 import Environment, BaseLoader

from data.database import get_db
from data import schemas
from services.config import ConfigService
from services.pages import PageService

# --- Dependency Setup ---
def get_page_service(db: Session = Depends(get_db)) -> PageService:
    return PageService(db)

router = APIRouter(tags=["Public"])

# --- Helper: String Template Rendering ---
def render_db_template(template_str: str, context: dict) -> str:
    """
    Renders a Jinja2 template stored as a string (from DB).
    Adds the 'tojson' filter manually to match standard web framework behavior.
    """
    env = Environment(loader=BaseLoader(), autoescape=True)
    
    # Define tojson filter to handle Python -> JSON string conversion for JS variables
    def to_json_filter(value: Any) -> str:
        return json.dumps(value, default=str) # default=str handles datetime objects safely
    
    env.filters['tojson'] = to_json_filter
    
    template = env.from_string(template_str)
    return template.render(**context)


# ==========================================
# 🖼️ HTML SERVING ROUTES
# ==========================================

@router.get("/", response_class=HTMLResponse)
def serve_home_page(page_service: PageService = Depends(get_page_service)):
    """Serves the page labeled as 'home'."""
    page = page_service.get_first_page_by_labels(['sys:home','any:read'])
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Critical: Home page not configured, notify site owner.")

    return HTMLResponse(content=page.html, status_code=200)

# ==========================================
# 🚀 PUBLIC API ROUTES
# ==========================================

@router.get("/api/{slug}", response_class=schemas.Page)
def serve_generic_page(slug: str, page_service: PageService = Depends(get_page_service)):
    page = page_service.get_page_by_slug(slug)
    if not page.labels or not {'sys:head', 'any:read'}.issubset(label.name for label in page.labels):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found in this category.")
    return page

@router.get("/api/{main}/{slug}", response_model=schemas.Page)
def api_get_any_page(main:str, slug: str, page_service: PageService = Depends(get_page_service)):
    page = page_service.get_page_by_slug(slug)
    
    if not page.labels or not {f'main:{main}', 'any:read'}.issubset(label.name for label in page.labels):
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found in this category.")

    return page

@router.get("/favicon.ico", include_in_schema=False)
async def get_favicon():
    return FileResponse("static/assets/favicon.ico", media_type="image/x-icon")


@router.get("/quiz", response_class=HTMLResponse)
def serve_quiz_page(request: Request):
    """Serves quiz page with PocketBase URL injected from CMS config."""
    service = ConfigService(next(get_db()))
    pb_url = service.get_setting_value("pb_url") or "http://localhost:8090"
    templates = Jinja2Templates(directory="static/competition")
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "api_base": pb_url}
    )

# ==========================================
# 🚀 DYNAMIC ROUTES
# ==========================================

@router.get("/{slug}", response_class=HTMLResponse)
def serve_top_level_page(
    slug: str,
    page_service: PageService = Depends(get_page_service),
):
    page = page_service.get_page_by_slug(slug)
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")

    label_names = {label.name for label in page.labels}
    required_labels = {"sys:head", "any:read"}

    if not required_labels.issubset(label_names):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    
    # 3. If it's already static HTML, return it
    if page.type == 'html':
        return HTMLResponse(content=page.html, status_code=200)

    # 4. Handle Markdown/Dynamic Pages (SSR)
    # Fetch the template
    markdown_template = page_service.get_first_page_by_labels(['sys:template', 'any:read'])
    if not markdown_template:
        raise HTTPException(status_code=500, detail="System Error: Markdown template missing.")
    
    context = {
        "title": page.title,
        "markdown_content": page.markdown,
        "author": page.author if hasattr(page, 'author') else "Unknown",
        "published": page.created if hasattr(page, 'created_at') else "",
        "updated": page.updated if hasattr(page, 'updated_at') else "",
        "description": page.content if hasattr(page, 'description') else "",
        "thumb": page.thumb if hasattr(page, 'thumbnail') else ""
    }

    # Render on Server
    rendered_html = render_db_template(markdown_template.html, context)
    
    return HTMLResponse(content=rendered_html, status_code=200)

    
@router.get("/{main}/{slug}", response_class=HTMLResponse)
def serve_any_post(slug: str, main:str, page_service: PageService = Depends(get_page_service)):
    """
    Serves a single page with SSR.
    1. Fetches the content page.
    2. Fetches the layout template.
    3. Renders the template with content injected before sending to client.
    """
    if main == slug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found.")
    
    # 1. Fetch the actual content page
    page = page_service.get_page_by_slug(slug) 
    
    # 2. Security/Logic Check
    if not page.labels or not {f'main:{main}', 'any:read'}.issubset(label.name for label in page.labels):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found.")

    # 3. If it's already static HTML, return it
    if page.type == 'html':
        return HTMLResponse(content=page.html, status_code=200)

    # 4. Handle Markdown/Dynamic Pages (SSR)
    # Fetch the template
    markdown_template = page_service.get_first_page_by_labels(['sys:template', 'any:read'])
    if not markdown_template:
        raise HTTPException(status_code=500, detail="System Error: Markdown template missing.")
    
    context = {
        "title": page.title,
        "markdown_content": page.markdown,
        "author": page.author if hasattr(page, 'author') else "Unknown",
        "published": page.created if hasattr(page, 'created_at') else "",
        "updated": page.updated if hasattr(page, 'updated_at') else "",
        "description": page.content if hasattr(page, 'description') else "",
        "thumb": page.thumb if hasattr(page, 'thumbnail') else ""
    }

    # Render on Server
    rendered_html = render_db_template(markdown_template.html, context)
    
    return HTMLResponse(content=rendered_html, status_code=200)


