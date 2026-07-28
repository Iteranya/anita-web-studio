# file: services/pages.py

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional

from data import crud, schemas, models

class PageService:
    def __init__(self, db: Session):
        self.db = db

    def get_page_by_slug(self, slug: str) -> models.Page:
        """
        Gets a page by slug, raising a standard 404 exception if not found.
        """
        page = crud.get_page(self.db, slug=slug)
        if not page:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page with slug '{slug}' not found."
            )
        return page

    def list_page_by_type(self, type:str, skip: int, limit: int) -> list[models.Page]:
        """Gets a list of all pages."""
        return crud.list_pages_by_type(self.db, type=type, skip=skip, limit=limit)

    def get_all_pages(self, skip: int, limit: int) -> list[models.Page]:
        """Gets a list of all pages."""
        return crud.list_pages(self.db, skip=skip, limit=limit)

    def create_new_page(self, page_data: schemas.PageCreate) -> models.Page:
        """
        Creates a new page after performing business logic checks.
        """
        # 1. Check for forbidden slugs.
        forbidden_slugs = {"admin", "api", "login", "static","blog"}
        if page_data.slug in forbidden_slugs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The slug '{page_data.slug}' is a reserved keyword."
            )

        # 2. Check for slug uniqueness.
        existing_page = crud.get_page(self.db, slug=page_data.slug)
        if existing_page:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Page with slug '{page_data.slug}' already exists."
            )

        # 3. If all checks pass, call the CRUD function to create the page.
        new_page = crud.create_page(self.db, page=page_data)

        return new_page
        
    def update_existing_page(self, slug: str, page_update_data: schemas.PageUpdate) -> models.Page:
        """
        Updates an existing page using the generic PageUpdate schema.
        """
        # Ensure the page exists
        db_page = self.get_page_by_slug(slug)
        
        # FIX: Pass the Pydantic model directly. Do not .model_dump() here.
        updated_page = crud.update_page(self.db, slug=db_page.slug, page_update=page_update_data)
        
        return updated_page


    def update_existing_page_markdown(
        self, slug: str, page_update_data: schemas.PageMarkdownUpdate
    ) -> models.Page:
        """
        Updates only Markdown fields of an existing page.
        """
        db_page = self.get_page_by_slug(slug)

        # FIX: Pass the Pydantic model directly. Do not .model_dump() here.
        updated_page = crud.update_page(self.db, slug=db_page.slug, page_update=page_update_data)
        return updated_page


    def update_existing_page_html(
        self, slug: str, page_update_data: schemas.PageUpdateHTML
    ) -> models.Page:
        """
        Updates only HTML fields of an existing page.
        """
        db_page = self.get_page_by_slug(slug)

        # FIX: Pass the Pydantic model directly. Do not .model_dump() here.
        # The CRUD layer (data/crud.py) expects a Pydantic model to call .model_dump() on it.
        updated_page = crud.update_page(self.db, slug=db_page.slug, page_update=page_update_data)
        return updated_page



    def delete_page_by_slug(self, slug: str):
        """
        Deletes a page.
        """
        # First, ensure the page exists.
        self.get_page_by_slug(slug)

        # Call the CRUD function.
        crud.delete_page(self.db, slug=slug)

        # Return nothing, as the router will handle the 204 response.

    # -----------------------------------------------------------------
    # ✨ NEW METHODS FOR TAG-BASED QUERIES ✨
    # -----------------------------------------------------------------

    def get_pages_by_label(self, label: str) -> List[models.Page]:
        """
        Retrieves all pages containing a specific label by calling the efficient
        CRUD function that filters in the database.
        """
        return crud.get_pages_by_label(self.db, label=label)
    
    def get_pages_by_author(self,author:str) -> List[models.Page]:
        """
        Retrieves all pages made by certain author.
        """
        return crud.get_pages_by_author(self.db,author)
    
    def get_pages_by_labels(self, labels: List[str]) -> List[models.Page]:
        """
        Retrieves all pages containing ALL of the given labels.
        """

        if not labels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one label must be provided."
            )

        # Normalize + join for the CRUD engine
        query_str = " ".join(labels)

        return crud.search_pages(self.db, query_str=query_str)
    
    def get_first_page_by_labels(self, label: List[str]) -> Optional[models.Page]:
        """
        Retrieves the most recent page with a specific label by calling the
        efficient CRUD function.
        """
        return crud.get_first_page_by_labels(self.db, label=label)

    def get_first_page_by_label(self, label: str) -> Optional[models.Page]:
        """
        Retrieves the most recent page with a specific label by calling the
        efficient CRUD function.
        """
        return crud.get_first_page_by_label(self.db, label=label)