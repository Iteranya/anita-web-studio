from fastapi import APIRouter, Depends, HTTPException, Response, status
from typing import List, Optional
from sqlalchemy.orm import Session
from data.database import get_db
from data import schemas 
from services.collections import CollectionService
from services.users import UserService
from src.dependencies import get_current_user, optional_user
from data.schemas import CurrentUser, SubmissionBase

# --- Dependency Setup ---
def get_collection_service(db: Session = Depends(get_db)) -> CollectionService:
    return CollectionService(db)

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)

router = APIRouter(prefix="/collections", tags=["Collection"])

# ----------------------------------------------------
# 🧩 FORMS CRUD
# ----------------------------------------------------

@router.post("/", response_model=schemas.Collection, status_code=status.HTTP_201_CREATED)
def create_collection(
    collection_in: schemas.CollectionCreate,
    collection_service: CollectionService = Depends(get_collection_service),
    user_service: UserService = Depends(get_user_service),  
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new custom collection."""
    user_permissions = user_service.get_user_permissions(user.username)
    can_create_collection = "*" in user_permissions or "collection:create" in user_permissions
    if can_create_collection:
        collection_in.author = user.username
        return collection_service.create_new_collection(collection_data=collection_in)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create a collection."
        )

@router.get("/list", response_model=List[schemas.Collection])
def list_collections(
    label: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    collection_service: CollectionService = Depends(get_collection_service),
    user_service: UserService = Depends(get_user_service),  
    user: CurrentUser = Depends(get_current_user),
):
    """List all available collections, optionally filtered by label."""
    user_permissions = user_service.get_user_permissions(user.username)
    can_read_collection = "*" in user_permissions or "collection:read" in user_permissions
    if not can_read_collection:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to read a collection."
        )
    
    all_collections = collection_service.get_all_collections(skip=skip, limit=limit)
    
    if label:
        # FIX: Iterate over f.labels (objects) and check if the label string matches .name
        return [
            f for f in all_collections 
            if f.labels and any(t.name == label for t in f.labels)
        ]
    
    return all_collections

@router.get("/{slug}", response_model=schemas.Collection)
def get_collection(
    slug: str,
    collection_service: CollectionService = Depends(get_collection_service),
    user_service: UserService = Depends(get_user_service),  
    user: CurrentUser = Depends(get_current_user),
):
    """Get a single collection by its slug."""
    user_permissions = user_service.get_user_permissions(user.username)
    can_read_collection = "*" in user_permissions or "collection:read" in user_permissions
    if not can_read_collection:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to read a collection."
        )
    return collection_service.get_collection_by_slug(slug)

@router.put("/{slug}", response_model=schemas.Collection)
def update_collection(
    slug: str,
    collection_update: schemas.CollectionUpdate,
    collection_service: CollectionService = Depends(get_collection_service),
    user_service: UserService = Depends(get_user_service),  
    user: CurrentUser = Depends(get_current_user),
):
    """Update an existing collection definition."""
    user_permissions = user_service.get_user_permissions(user.username)
    can_update_collection = "*" in user_permissions or "collection:update" in user_permissions
    if not can_update_collection:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update a collection."
        )
    return collection_service.update_existing_collection(slug=slug, collection_update_data=collection_update)

@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    slug: str,
    collection_service: CollectionService = Depends(get_collection_service),
    user_service: UserService = Depends(get_user_service),  
    user: CurrentUser = Depends(get_current_user),
):
    """Delete a collection and all its submissions by its slug."""
    user_permissions = user_service.get_user_permissions(user.username)
    can_delete_collection = "*" in user_permissions or "collection:delete" in user_permissions
    if not can_delete_collection:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete a collection."
        )
    collection_service.delete_collection_by_slug(slug)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# ----------------------------------------------------
# 🏷️ TAG UTILITIES
# ----------------------------------------------------

@router.get("/labels/all", response_model=List[str])
def get_all_labels(
    collection_service: CollectionService = Depends(get_collection_service),
    user: CurrentUser = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),  
):
    """Get a list of all unique labels across all collections."""
    user_permissions = user_service.get_user_permissions(user.username)
    permission = "*" in user_permissions or "collection:read" in user_permissions
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this route."
        )
    collections = collection_service.get_all_collections(skip=0, limit=1000)
    
    labels = set()
    for collection in collections:
        if collection.labels:
            # FIX: Extract .name from the objects
            labels.update(label.name for label in collection.labels) 
    return sorted(list(labels))

# ----------------------------------------------------
# 📨 FORM SUBMISSIONS
# ----------------------------------------------------

@router.post("/{slug}/submit", response_model=schemas.Submission, status_code=status.HTTP_201_CREATED)
def submit_collection(
    slug: str,
    submission_body: SubmissionBase,
    collection_service: CollectionService = Depends(get_collection_service),
    user_service: UserService = Depends(get_user_service),  
    user: CurrentUser = Depends(optional_user),
):
    """Submit a response to a collection."""
    collection = collection_service.get_collection_by_slug(slug)
    
    # FIX: Convert list of objects to set of strings
    collection_label_names = {label.name for label in (collection.labels or [])}

    user_permissions = []
    user_role = "anon" 

    if user:
        user_permissions = user_service.get_user_permissions(user.username)
        user_role = user.role

    override_submission = "*" in user_permissions or "submission:create" in user_permissions
    # FIX: Check against the string set
    collection_is_open = "any:create" in collection_label_names
    
    role_is_allowed = f"{user_role}:create" in collection_label_names

    if override_submission:
        pass
    elif role_is_allowed:
        pass
    elif collection_is_open:
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to add submission in this collection."
        )
    
    author_username = user.username if user else "Anon"
    
    submission_data = schemas.SubmissionCreate(
        collection_slug=slug,
        data=submission_body.data,
        custom=submission_body.custom,
        author=author_username
    )
    
    return collection_service.create_new_submission(submission_data=submission_data)

@router.get("/{slug}/submissions", response_model=List[schemas.Submission])
def list_submissions(
    slug: str,
    skip: int = 0,
    limit: int = 100,
    collection_service: CollectionService = Depends(get_collection_service),
    user_service: UserService = Depends(get_user_service),  
    user: CurrentUser = Depends(get_current_user),
):
    """List all submissions for a collection."""
    collection = collection_service.get_collection_by_slug(slug)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # FIX: Extract label names
    collection_label_names = {label.name for label in (collection.labels or [])}

    user_permissions = user_service.get_user_permissions(user.username)
    override_submission = "*" in user_permissions or "submission:read" in user_permissions
    
    # FIX: Check against string set
    collection_is_open = "any:read" in collection_label_names
    role_is_allowed = f"{user.role}:read" in collection_label_names
    
    if not override_submission and not collection_is_open and not role_is_allowed:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        
    return collection_service.get_submissions_for_collection(collection_slug=slug, skip=skip, limit=limit)

@router.get("/{slug}/submissions/{submission_id}", response_model=schemas.Submission)
def get_submission(
    slug: str,
    submission_id: int,
    collection_service: CollectionService = Depends(get_collection_service),
    user_service: UserService = Depends(get_user_service),
    user: CurrentUser = Depends(get_current_user),
):
    collection = collection_service.get_collection_by_slug(slug)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    submission = collection_service.get_submission_by_id(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # FIX: Extract label names
    collection_label_names = {label.name for label in (collection.labels or [])}

    user_permissions = user_service.get_user_permissions(user.username)

    override_submission = ("*" in user_permissions or "submission:read" in user_permissions)
    
    # FIX: Check against string set
    collection_is_open = "any:read" in collection_label_names
    role_is_allowed = f"{user.role}:read" in collection_label_names
    user_owns_it = submission.author == user.username

    authorized = (
        override_submission or
        collection_is_open or
        role_is_allowed or
        user_owns_it
    )

    if not authorized:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if submission.collection_slug != slug:
        raise HTTPException(status_code=404, detail="Submission not found for this collection.")

    return submission


@router.put("/{slug}/submissions/{submission_id}", response_model=schemas.Submission)
def update_submission(
    slug: str,
    submission_id: int,
    submission_update: schemas.SubmissionUpdate,
    collection_service: CollectionService = Depends(get_collection_service),
    user: Optional[CurrentUser] = Depends(optional_user),
    user_service: UserService = Depends(get_user_service),
):
    collection = collection_service.get_collection_by_slug(slug)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # FIX: Extract label names once
    collection_label_names = {label.name for label in (collection.labels or [])}

    if user is None:
        # FIX: Check against string set
        if "any:update" not in collection_label_names:
            raise HTTPException(status_code=404, detail="Submission not found")

    submission = collection_service.get_submission_by_id(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # FIX: Handle permissions safely for optional user
    user_permissions = []
    user_role = "anon"
    if user:
        user_permissions = user_service.get_user_permissions(user.username)
        user_role = user.role

    override_update = ("*" in user_permissions or "submission:update" in user_permissions)

    # FIX: Check against string set using safe variables
    collection_is_open_for_update = "any:update" in collection_label_names
    role_is_allowed = f"{user_role}:update" in collection_label_names
    user_owns_it = user and submission.author == user.username

    authorized = (
        override_update or
        collection_is_open_for_update or
        role_is_allowed or
        user_owns_it
    )

    if not authorized:
        raise HTTPException(status_code=404, detail="Submission not found")

    if submission.collection_slug != slug:
        raise HTTPException(status_code=404, detail="Submission not found for this collection.")

    return collection_service.update_submission(submission_id=submission_id, submission_data=submission_update)


@router.delete("/{slug}/submissions/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_submission(
    slug: str,
    submission_id: int,
    collection_service: CollectionService = Depends(get_collection_service),
    user: Optional[CurrentUser] = Depends(optional_user),
    user_service: UserService = Depends(get_user_service),
):
    collection = collection_service.get_collection_by_slug(slug)
    if not collection:
        raise HTTPException(status_code=404, detail="Submission not found")

    # FIX: Extract label names once
    collection_label_names = {label.name for label in (collection.labels or [])}

    if user is None:
        # FIX: Check against string set
        if "any:delete" not in collection_label_names:
            raise HTTPException(status_code=404, detail="Submission not found")

    submission = collection_service.get_submission_by_id(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # FIX: Handle permissions safely for optional user
    user_permissions = []
    user_role = "anon"
    if user:
        user_permissions = user_service.get_user_permissions(user.username)
        user_role = user.role

    override_delete = ("*" in user_permissions or "submission:delete" in user_permissions)

    # FIX: Check against string set using safe variables
    collection_is_open_for_delete = "any:delete" in collection_label_names
    role_is_allowed = f"{user_role}:delete" in collection_label_names
    user_owns_it = user and submission.author == user.username

    authorized = (
        override_delete or
        collection_is_open_for_delete or
        role_is_allowed or
        user_owns_it
    )

    if not authorized:
        raise HTTPException(status_code=404, detail="Submission not found")

    if submission.collection_slug != slug:
        raise HTTPException(status_code=404, detail="Submission not found")

    collection_service.delete_submission_by_id(submission_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

