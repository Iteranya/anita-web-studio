from fastapi import APIRouter, Depends, HTTPException, Response, status
from typing import List, Optional, Set
from sqlalchemy.orm import Session

from data.database import get_db
from data import schemas
from data.schemas import CurrentUser
from services.pages import PageService
from services.users import UserService
from src import dependencies as dep
from src.audit import logger

# TODO: Figure out what the user can fetch *before* fetching from database for performance.

# --- Dependency Setup ---

def get_page_service(db: Session = Depends(get_db)) -> PageService:
    return PageService(db)

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)

router = APIRouter(prefix="/page", tags=["Pages"])

# --- Helper Logic ---

def get_label_names(db_labels) -> Set[str]:
    """Extract string names from SQLAlchemy label objects."""
    if not db_labels:
        return set()
    return {t.name for t in db_labels}

def check_type_permission(permissions: List[str], page_type: str, action: str):
    """
    Validates if user has specific editor permissions (Aina vs Asta).
    e.g. check_type_permission(perms, 'html', 'create') looks for 'html:create'
    """
    required_perm = f"{page_type}:{action}"
    
    # Check for specific permission OR super-admin wildcard
    if "*" in permissions or required_perm in permissions:
        return True
    return False

# ----------------------------------------------------
# 📄 PAGES CRUD
# ----------------------------------------------------

@router.post("/", response_model=schemas.Page, status_code=status.HTTP_201_CREATED)
def create_page(
    page_in: schemas.PageCreate,
    page_service: PageService = Depends(get_page_service),
    user_service: UserService = Depends(get_user_service),  
    user: CurrentUser = Depends(dep.get_current_user),  
):
    # 0. Enforce Default Type
    # If type is None or empty, default to 'markdown'
    if not page_in.type:
        page_in.type = "markdown"

    permissions = user_service.get_user_permissions(user.username)
    
    # 1. Base Page Permission
    can_create_page = "*" in permissions or "page:create" in permissions
    
    # 2. Type Specific Permission (Aina vs Asta)
    if page_in.type == "markdown":
        can_create_type = True
    else:
        can_create_type = check_type_permission(permissions, page_in.type, "create")

    if not can_create_page:
        raise HTTPException(status_code=403, detail="You do not have permission to create pages.")
        
    if not can_create_type:
        raise HTTPException(
            status_code=403, 
            detail=f"You do not have permission to create {page_in.type} pages."
        )

    # 3. Seed 'custom' data from the default page template
    default_page = page_service.get_page_by_slug("default-page")
    if default_page and default_page.custom:
        page_in.custom = default_page.custom

    page_in.author = user.username
    logger.info(f"User {user.username} creating {page_in.type} page: {page_in.slug}")
    return page_service.create_new_page(page_data=page_in)


@router.get("/list", response_model=List[schemas.PageData])
def list_pages(
    skip: int = 0,
    limit: int = 100,
    page_service: PageService = Depends(get_page_service),
    user_service: UserService = Depends(get_user_service),
    user: Optional[CurrentUser] = Depends(dep.optional_user),
):
    # Standard listing (Read access logic)
    all_pages = page_service.get_all_pages(skip=skip, limit=limit)
    
    user_permissions = []
    user_role = "anon"
    if user:
        user_permissions = user_service.get_user_permissions(user.username)
        user_role = user.role

    if "*" in user_permissions or "page:read" in user_permissions:
        return all_pages

    accessible_pages = []
    for page in all_pages:
        label_names = get_label_names(page.labels)
        
        is_public = "any:read" in label_names
        role_allowed = f"{user_role}:read" in label_names
        is_author = user and page.author == user.username

        if is_public or role_allowed or is_author:
            accessible_pages.append(page)

    return accessible_pages

@router.get("/list/markdown", response_model=List[schemas.PageData])
def list_markdown_pages(
    skip: int = 0,
    limit: int = 100,
    page_service: PageService = Depends(get_page_service),
    user_service: UserService = Depends(get_user_service),
    user: Optional[CurrentUser] = Depends(dep.optional_user),
):
    all_pages = page_service.list_page_by_type("markdown", skip=skip, limit=limit)

    user_permissions = []
    user_role = "anon"
    if user:
        user_permissions = user_service.get_user_permissions(user.username)
        user_role = user.role

    if "*" in user_permissions or "page:read" in user_permissions:
        return all_pages

    accessible_pages = []
    for page in all_pages:
        label_names = get_label_names(page.labels)
        is_public = "any:read" in label_names
        role_allowed = f"{user_role}:read" in label_names
        is_author = user and page.author == user.username
        if is_public or role_allowed or is_author:
            accessible_pages.append(page)

    return accessible_pages

@router.get("/list/html", response_model=List[schemas.PageData])
def list_markdown_pages(
    skip: int = 0,
    limit: int = 100,
    page_service: PageService = Depends(get_page_service),
    user_service: UserService = Depends(get_user_service),
    user: Optional[CurrentUser] = Depends(dep.optional_user),
):
    all_pages = page_service.list_page_by_type("html", skip=skip, limit=limit)

    user_permissions = []
    user_role = "anon"
    if user:
        user_permissions = user_service.get_user_permissions(user.username)
        user_role = user.role

    if "*" in user_permissions or "page:read" in user_permissions:
        return all_pages

    accessible_pages = []
    for page in all_pages:
        label_names = get_label_names(page.labels)
        is_public = "any:read" in label_names
        role_allowed = f"{user_role}:read" in label_names
        is_author = user and page.author == user.username
        if is_public or role_allowed or is_author:
            accessible_pages.append(page)

    return accessible_pages


@router.get("/{slug}", response_model=schemas.Page)
def get_page(
    slug: str,
    page_service: PageService = Depends(get_page_service),
    user_service: UserService = Depends(get_user_service),
    user: Optional[CurrentUser] = Depends(dep.optional_user),
):
    page = page_service.get_page_by_slug(slug)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    label_names = get_label_names(page.labels)
    
    # 1. Public Access (No type check needed just to view the website)
    if "any:read" in label_names:
        return page

    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    user_permissions = user_service.get_user_permissions(user.username)
    
    # 2. Access Rights
    is_admin = "*" in user_permissions or "page:read" in user_permissions
    role_allowed = f"{user.role}:read" in label_names
    is_author = page.author == user.username

    if is_admin or role_allowed or is_author:
        return page

    raise HTTPException(status_code=404, detail="Page not found")


@router.put("/{slug}", response_model=schemas.Page)
def update_page(
    slug: str,
    page_update: schemas.PageUpdate,
    page_service: PageService = Depends(get_page_service),
    user_service: UserService = Depends(get_user_service),
    user: CurrentUser = Depends(dep.get_current_user),
):
    """
    Updates page metadata or content.
    Checks BOTH page ownership/labels AND editor capability (Aina/Asta).
    """
    db_page = page_service.get_page_by_slug(slug)
    if not db_page:
        raise HTTPException(status_code=404, detail="Page not found")

    label_names = get_label_names(db_page.labels)
    user_permissions = user_service.get_user_permissions(user.username)

    # 1. Access Rights (Can I touch this page?)
    is_admin = "*" in user_permissions or "page:update" in user_permissions
    is_author = db_page.author == user.username
    role_allowed = f"{user.role}:update" in label_names
    is_open_update = "any:update" in label_names

    has_access_right = (is_admin or is_author or role_allowed or is_open_update)

    if not has_access_right:
        raise HTTPException(status_code=403, detail="Permission denied for this page.")

    # 2. Capability Rights (Can I use this editor?)
    # We check the CURRENT page type.
    can_edit_current_type = check_type_permission(user_permissions, db_page.type, "update")

    if not can_edit_current_type:
         raise HTTPException(
            status_code=403, 
            detail=f"You lack permission to update {db_page.type} content."
        )

    # 3. Type Change Check (Edge Case)
    # If the user is trying to switch types (e.g. Markdown -> HTML)
    if page_update.type and page_update.type != db_page.type:
        # User needs permission to CREATE the new type
        can_create_new_type = check_type_permission(user_permissions, page_update.type, "create")
        if not can_create_new_type:
            raise HTTPException(
                status_code=403, 
                detail=f"You lack permission to change page type to {page_update.type}."
            )

    logger.info(f"User '{user.username}' updating page '{slug}'")
    return page_service.update_existing_page(slug=slug, page_update_data=page_update)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_page(
    slug: str,
    page_service: PageService = Depends(get_page_service),
    user_service: UserService = Depends(get_user_service), 
    user: CurrentUser = Depends(dep.get_current_user),
):
    db_page = page_service.get_page_by_slug(slug)
    if not db_page:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    label_names = get_label_names(db_page.labels)
    user_permissions = user_service.get_user_permissions(user.username)

    # 1. Access Rights
    is_admin = "*" in user_permissions or "page:delete" in user_permissions
    is_author = db_page.author == user.username
    role_allowed = f"{user.role}:delete" in label_names

    if not (is_admin or is_author or role_allowed):
        raise HTTPException(status_code=403, detail="Permission denied")

    # 2. Capability Rights (Physically Impossible But Nice To Have)
    can_delete_type = check_type_permission(user_permissions, db_page.type, "delete")
    
    if not can_delete_type:
        raise HTTPException(
            status_code=403, 
            detail=f"You lack permission to delete {db_page.type} pages."
        )

    logger.info(f"User {user.username} deleted page: {slug}")
    page_service.delete_page_by_slug(slug)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# ----------------------------------------------------
# ✏️ SPECIALIZED UPDATES
# ----------------------------------------------------

@router.put("/{slug}/markdown", response_model=schemas.Page)
def update_page_markdown(
    slug: str,
    page_update: schemas.PageMarkdownUpdate,
    page_service: PageService = Depends(get_page_service),
    user_service: UserService = Depends(get_user_service),
    user: CurrentUser = Depends(dep.get_current_user),
):
    db_page = page_service.get_page_by_slug(slug)
    if not db_page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    # 1. Check if page is actually markdown (Sanity check)
    if db_page.type != "markdown":
         raise HTTPException(status_code=400, detail="Endpoint only for markdown pages.")

    label_names = get_label_names(db_page.labels)
    user_permissions = user_service.get_user_permissions(user.username)

    # 2. Access Rights
    authorized_access = (
        "*" in user_permissions or 
        "page:update" in user_permissions or 
        db_page.author == user.username or 
        f"{user.role}:update" in label_names or
        "any:update" in label_names
    )

    if not authorized_access:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 3. Capability Rights (Asta Access)
    can_update_markdown = check_type_permission(user_permissions, "markdown", "update")
    
    if not can_update_markdown:
        raise HTTPException(status_code=403, detail="Missing 'markdown:update' permission.")

    return page_service.update_existing_page_markdown(slug=slug, page_update_data=page_update)


@router.put("/{slug}/html", response_model=schemas.Page)
def update_page_html(
    slug: str,
    page_update: schemas.PageUpdateHTML,
    page_service: PageService = Depends(get_page_service),
    user_service: UserService = Depends(get_user_service),
    user: CurrentUser = Depends(dep.get_current_user),
):
    db_page = page_service.get_page_by_slug(slug)
    if not db_page:
        raise HTTPException(status_code=404, detail="Page not found")

    # 1. Check if page is actually html
    if db_page.type != "html":
         raise HTTPException(status_code=400, detail="Endpoint only for html pages.")

    label_names = get_label_names(db_page.labels)
    user_permissions = user_service.get_user_permissions(user.username)

    # 2. Access Rights
    authorized_access = (
        "*" in user_permissions or 
        "page:update" in user_permissions or 
        db_page.author == user.username or 
        f"{user.role}:update" in label_names or
        "any:update" in label_names
    )

    if not authorized_access:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # 3. Capability Rights (Aina Access)
    can_update_html = check_type_permission(user_permissions, "html", "update")
    
    if not can_update_html:
        raise HTTPException(status_code=403, detail="Missing 'html:update' permission.")

    return page_service.update_existing_page_html(slug=slug, page_update_data=page_update)