from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status, Body
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from data.database import get_db
from data import schemas
from services.collections import CollectionService
from services.users import UserService
from src.dependencies import get_current_user, optional_user
from data.schemas import CurrentUser

# --- Dependency Setup ---
def get_collection_service(db: Session = Depends(get_db)) -> CollectionService:
    return CollectionService(db)

def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)

# We use a PocketBase-like naming convention: /api/collections/{slug}/records
router = APIRouter(prefix="/api", tags=["API Records (PocketBase-style)"])

# ----------------------------------------------------
# 🛠️ HELPER FUNCTIONS
# ----------------------------------------------------

def format_record(submission_orm: Any) -> Dict[str, Any]:
    """
    Flattens a submission so that the 'data' fields sit at the root, 
    alongside metadata like id, created, and author.
    """
    # Validate and serialize ORM to Pydantic model first
    sub = schemas.Submission.model_validate(submission_orm)
    
    # Start with the raw schema data at the root
    flat_record = sub.data.copy() if sub.data else {}
    
    # Inject metadata at the top level 
    # (Note: These will overwrite schema fields if a user named a field 'id' or 'created')
    flat_record["id"] = sub.id
    flat_record["collectionId"] = sub.collection_slug 
    flat_record["created"] = sub.created
    flat_record["updated"] = sub.updated
    flat_record["author"] = sub.author
    
    # Optional fields
    if sub.custom:
        flat_record["custom"] = sub.custom
    if sub.labels:
        flat_record["labels"] = sub.labels
    if sub.tags:
        flat_record["tags"] = sub.tags
        
    return flat_record


# ----------------------------------------------------
# 📝 RECORD CRUD (PocketBase-style)
# ----------------------------------------------------

@router.post("/collections/{slug}/records", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
def create_record(
    slug: str,
    payload: Dict[str, Any] = Body(..., description="The flat JSON body matching the collection schema"),
    collection_service: CollectionService = Depends(get_collection_service),
    user_service: UserService = Depends(get_user_service),  
    user: CurrentUser = Depends(optional_user),
):
    """Create a new record, extracting tags/labels from the flat payload."""
    collection = collection_service.get_collection_by_slug(slug)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    collection_label_names = {label.name for label in (collection.labels or [])}
    user_permissions = []
    user_role = "anon" 

    if user:
        user_permissions = user_service.get_user_permissions(user.username)
        user_role = user.role

    override_submission = "*" in user_permissions or "submission:create" in user_permissions
    collection_is_open = "any:create" in collection_label_names
    role_is_allowed = f"{user_role}:create" in collection_label_names

    if not (override_submission or role_is_allowed or collection_is_open):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    
    author_username = user.username if user else "Anon"
    
    # 1. Extract reserved fields from the flat payload
    tags = payload.pop("tags", [])
    labels = payload.pop("labels", [])
    custom = payload.pop("custom", {})

    # 2. What's left in 'payload' is purely the user's custom schema data
    submission_data = schemas.SubmissionCreate(
        collection_slug=slug,
        data=payload,
        custom=custom,
        tags=tags,
        labels=labels,
        author=author_username
    )
    
    submission = collection_service.create_new_submission(submission_data=submission_data)
    return format_record(submission)


@router.get("/collections/{slug}/records", response_model=List[Dict[str, Any]])
def list_records(
    slug: str,
    # Make skip default to 0, but ensure it can't be negative
    skip: Optional[int] = Query(0, ge=0, description="Number of records to skip"),
    # Make limit default to None (no limit), but if provided, must be at least 1
    limit: Optional[int] = Query(None, ge=1, description="Max records to return. Omit to get all."),
    collection_service: CollectionService = Depends(get_collection_service),
    user_service: UserService = Depends(get_user_service),  
    user: CurrentUser = Depends(optional_user),
):
    """List all records for a collection, flattened."""
    collection = collection_service.get_collection_by_slug(slug)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    collection_label_names = {label.name for label in (collection.labels or [])}
    collection_is_open = "any:read" in collection_label_names
    if user:
        user_permissions = user_service.get_user_permissions(user.username)
        override_submission = "*" in user_permissions or "submission:read" in user_permissions
    
        role_is_allowed = f"{user.role}:read" in collection_label_names
    
        if not (override_submission or collection_is_open or role_is_allowed):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        
    submissions = collection_service.get_submissions_for_collection(
        collection_slug=slug, 
        skip=skip, 
        limit=limit
    )
    return [format_record(sub) for sub in submissions]

@router.get("/collections/{slug}/records/{record_slug}", response_model=Dict[str, Any])
def get_record(
    slug: str,
    record_slug: str,
    collection_service: CollectionService = Depends(get_collection_service),
    user_service: UserService = Depends(get_user_service),
    user: CurrentUser = Depends(optional_user),
):
    """Get a single record by its ID, flattened."""
    collection = collection_service.get_collection_by_slug(slug)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    submission = collection_service.get_submission_by_id(record_slug)
    if not submission or submission.collection_slug != slug:
        raise HTTPException(status_code=404, detail="Record not found")

    collection_label_names = {label.name for label in (collection.labels or [])}
    collection_is_open = "any:read" in collection_label_names
    if user:
        user_permissions = user_service.get_user_permissions(user.username)
        override_submission = "*" in user_permissions or "submission:read" in user_permissions
        role_is_allowed = f"{user.role}:read" in collection_label_names
        user_owns_it = submission.author == user.username

        if not (override_submission or collection_is_open or role_is_allowed or user_owns_it):
            raise HTTPException(status_code=404, detail="Record not found")

    return format_record(submission)


@router.patch("/collections/{slug}/records/{record_id}", response_model=Dict[str, Any])
def update_record(
    slug: str,
    record_id: int,
    payload: Dict[str, Any] = Body(..., description="The flat JSON object with updated fields"),
    collection_service: CollectionService = Depends(get_collection_service),
    user: Optional[CurrentUser] = Depends(optional_user),
    user_service: UserService = Depends(get_user_service),
):
    """Update an existing record, extracting tags/labels from the flat payload."""
    collection = collection_service.get_collection_by_slug(slug)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    collection_label_names = {label.name for label in (collection.labels or [])}

    if user is None and "any:update" not in collection_label_names:
        raise HTTPException(status_code=404, detail="Record not found")

    submission = collection_service.get_submission_by_id(record_id)
    if not submission or submission.collection_slug != slug:
        raise HTTPException(status_code=404, detail="Record not found")

    user_permissions = []
    user_role = "anon"
    if user:
        user_permissions = user_service.get_user_permissions(user.username)
        user_role = user.role

    override_update = "*" in user_permissions or "submission:update" in user_permissions
    collection_is_open_for_update = "any:update" in collection_label_names
    role_is_allowed = f"{user_role}:update" in collection_label_names
    user_owns_it = user and submission.author == user.username

    if not (override_update or collection_is_open_for_update or role_is_allowed or user_owns_it):
        raise HTTPException(status_code=404, detail="Record not found")

    # 1. Extract reserved fields
    # We use .pop(..., None) so we don't accidentally overwrite existing arrays with [] 
    # if the user didn't include them in the PATCH request
    tags = payload.pop("tags", None)
    labels = payload.pop("labels", None)
    custom = payload.pop("custom", None)
    
    # Strip read-only server fields before building update model
    READONLY_FIELDS = {"id", "collectionId", "created", "updated", "author"}
    payload = {k: v for k, v in payload.items() if k not in READONLY_FIELDS}

    # 2. Build the update model
    submission_update = schemas.SubmissionUpdate(
        data=payload if payload else None,  # Only update data if schema fields were provided
        custom=custom,
        labels=labels,
        tags=tags 
    )

    updated_submission = collection_service.update_submission(submission_id=record_id, submission_data=submission_update)
    return format_record(updated_submission)


@router.delete("/collections/{slug}/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(
    slug: str,
    record_id: int,
    collection_service: CollectionService = Depends(get_collection_service),
    user: Optional[CurrentUser] = Depends(optional_user),
    user_service: UserService = Depends(get_user_service),
):
    """Delete a record."""
    collection = collection_service.get_collection_by_slug(slug)
    if not collection:
        raise HTTPException(status_code=404, detail="Record not found")

    collection_label_names = {label.name for label in (collection.labels or [])}

    if user is None and "any:delete" not in collection_label_names:
        raise HTTPException(status_code=404, detail="Record not found")

    submission = collection_service.get_submission_by_id(record_id)
    if not submission or submission.collection_slug != slug:
        raise HTTPException(status_code=404, detail="Record not found")

    user_permissions = []
    user_role = "anon"
    if user:
        user_permissions = user_service.get_user_permissions(user.username)
        user_role = user.role

    override_delete = "*" in user_permissions or "submission:delete" in user_permissions
    collection_is_open_for_delete = "any:delete" in collection_label_names
    role_is_allowed = f"{user_role}:delete" in collection_label_names
    user_owns_it = user and submission.author == user.username

    if not (override_delete or collection_is_open_for_delete or role_is_allowed or user_owns_it):
        raise HTTPException(status_code=404, detail="Record not found")

    collection_service.delete_submission_by_id(record_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)



# ----------------------------------------------------
# 📖 INSTANT API DISCOVERY & SCHEMA
# ----------------------------------------------------

def get_augmented_schema(base_schema: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Injects the flat API's built-in root fields into the collection's schema.
    Detects if the schema uses a `{"fields": [...]}` array format and adapts to it.
    """
    import copy
    augmented = copy.deepcopy(base_schema) if base_schema else {}
    
    # 1. Handle your custom Form-Builder format: {"fields": [...]}
    if "fields" in augmented and isinstance(augmented["fields"], list):
        augmented["fields"].extend([
            {
                "name": "tags",
                "label": "Tags",
                "type": "array",
                "required": False,
                "description": "Optional list of tags"
            },
            {
                "name": "labels",
                "label": "Labels",
                "type": "array",
                "required": False,
                "description": "Optional list of labels (e.g., status)"
            },
            {
                "name": "custom",
                "label": "Custom Data",
                "type": "object",
                "required": False,
                "description": "Optional unstructured JSON metadata"
            }
        ])
    # 2. Fallback for standard JSON Schema or empty schemas
    else:
        augmented["tags"] = {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional list of tags for this record"
        }
        augmented["labels"] = {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional list of labels for this record"
        }
        augmented["custom"] = {
            "type": "object",
            "additionalProperties": True,
            "description": "Optional unstructured JSON metadata"
        }
        
    return augmented


@router.get("/collections/discover", response_model=Dict[str, Any])
def discover_api(
    request: Request,
    collection_service: CollectionService = Depends(get_collection_service),
    user_service: UserService = Depends(get_user_service),
    user: Optional[CurrentUser] = Depends(optional_user),
):
    """
    Instant Documentation: Returns available API endpoints, usage instructions, 
    and the schemas (including tags/labels) for all accessible collections.
    """
    user_permissions = []
    user_role = "anon"
    if user:
        user_permissions = user_service.get_user_permissions(user.username)
        user_role = user.role

    # Fetch collections
    collections = collection_service.get_all_collections(skip=0, limit=1000)
    accessible_collections = {}
    base_url = str(request.base_url).rstrip("/") + router.prefix

    for coll in collections:
        labels = {label.name for label in (coll.labels or [])}
        
        # Check if user has permission to even know this collection exists
        can_read = "*" in user_permissions or "collection:read" in user_permissions
        is_open = "any:read" in labels or "any:create" in labels
        role_allowed = f"{user_role}:read" in labels or f"{user_role}:create" in labels

        if can_read or is_open or role_allowed:
            accessible_collections[coll.slug] = {
                "title": coll.title,
                "description": coll.description,
                # Inject tags and labels into the schema output
                "schema": get_augmented_schema(coll.schema),
                "endpoints": {
                    "schema": f"GET {base_url}/{coll.slug}/schema",
                    "list": f"GET {base_url}/{coll.slug}/records",
                    "get_one": f"GET {base_url}/{coll.slug}/records/{{id}}",
                    "create": f"POST {base_url}/{coll.slug}/records",
                    "update": f"PATCH {base_url}/{coll.slug}/records/{{id}}",
                    "delete": f"DELETE {base_url}/{coll.slug}/records/{{id}}"
                }
            }

    return {
        "_meta": {
            "api_style": "PocketBase-like (Flat JSON Records)",
            "description": "Send and receive flat JSON objects. System fields (tags, labels, custom) and Metadata (id, created, author) sit at the root alongside your dynamic schema data.",
            "auth_status": f"Logged in as {user.username} ({user_role})" if user else "Anonymous",
        },
        "collections": accessible_collections
    }


@router.get("/collections/{slug}/schema", response_model=Dict[str, Any])
def get_collection_schema(
    slug: str,
    collection_service: CollectionService = Depends(get_collection_service),
    user_service: UserService = Depends(get_user_service),
    user: Optional[CurrentUser] = Depends(optional_user),
):
    """Get the full JSON schema (including tags and labels) for a specific collection."""
    collection = collection_service.get_collection_by_slug(slug)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    collection_label_names = {label.name for label in (collection.labels or [])}
    
    user_permissions = []
    user_role = "anon"
    if user:
        user_permissions = user_service.get_user_permissions(user.username)
        user_role = user.role

    # Same access rules: if they can read or create records, they can see the schema
    can_read = "*" in user_permissions or "collection:read" in user_permissions
    is_open = "any:read" in collection_label_names or "any:create" in collection_label_names
    role_allowed = f"{user_role}:read" in collection_label_names or f"{user_role}:create" in collection_label_names

    if not (can_read or is_open or role_allowed):
        raise HTTPException(status_code=403, detail="Unauthorized to view this schema")

    # Return the schema with tags and labels seamlessly injected
    return get_augmented_schema(collection.schema)