import os
import sys
import shutil
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# --- Configuration & Environment Loading ---
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Load environment variables
load_dotenv(ENV_PATH)

sys.path.append(str(BASE_DIR))

# Import database (after path setup)
from data import database

# Import all route modules
from routes import (
    admin_route,
    auth_route,
    file_route,
    media_route,
    pages_route, 
    public_route,
    roles_route,
    config_route,
    pb_proxy,
    editor_route,
)

# --- Interactive Setup Helper ---
def interactive_setup():
    """
    Handles initial setup:
    1. Selects a database template (Theme) if anita.db is missing.
    2. Generates JWT_SECRET if missing from .env.
    """
    
    # 1. Database / Theme Selection
    db_path = BASE_DIR / "anita.db"
    templates_dir = BASE_DIR / "anita-template"

    if not db_path.exists():
        print("\n⚠️  No database found (anita.db).")
        
        # Find .db files in templates folder
        if not templates_dir.exists():
            os.makedirs(templates_dir)
            
        available_templates = list(templates_dir.glob("*.db"))
        
        if not available_templates:
            print("❌ No database templates found in /anita-template folder!")
            print("Please place your template .db files there and restart.")
            sys.exit(1)
        print("🏗️  Welcome to Anita CMS Setup!")
        print("   We need to initialize your database.")
        print("   Since this is a new installation, please select a Starter Template.")
        print("   (This will configure your initial pages, roles, and settings)")

        print("\n📂 Available Starter Templates:")
        for idx, temp in enumerate(available_templates, 1):
            print(f"   [{idx}] {temp.name}")

        selected_index = -1
        while selected_index < 0 or selected_index >= len(available_templates):
            try:
                choice = input("\nEnter the number of your choice: ")
                selected_index = int(choice) - 1
            except ValueError:
                pass

        selected_template = available_templates[selected_index]
        print(f"🔄 Copying '{selected_template.name}' to 'anita.db'...")
        shutil.copy(selected_template, db_path)
        print("✅ Database initialized successfully.\n")
    
    # 2. JWT Secret Generation
    # Reload env in case it was created/modified externally since script start
    load_dotenv(ENV_PATH, override=True)
    
    if not os.getenv("JWT_SECRET"):
        print("🔑 JWT_SECRET not found in .env.")
        gen_choice = input("Generate a secure random secret now? [Y/n]: ").strip().lower()
        
        if gen_choice in ["", "y", "yes", "Y"]:
            secret = secrets.token_hex(32)
            
            # Read current .env content
            content = ""
            if ENV_PATH.exists():
                with open(ENV_PATH, "r") as f:
                    content = f.read()
            
            # Append new secret
            prefix = "\n" if content and not content.endswith("\n") else ""
            with open(ENV_PATH, "a") as f:
                f.write(f"{prefix}JWT_SECRET={secret}\n")
            
            print("✅ Generated new JWT_SECRET and saved to .env.")
            # Reload environment to apply the change immediately
            load_dotenv(ENV_PATH, override=True)
        else:
            print("❌ Cannot proceed without JWT_SECRET. Exiting.")
            sys.exit(1)

# --- Database Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This code runs on startup
    print("🚀 Application starting up...")
    
    # Ensure tables exist (Safety check, though the copied DB should have them)
    database.Base.metadata.create_all(bind=database.engine)
        
    yield # The application runs here

    # This code runs on shutdown
    print("👋 Application shutting down...")


# --- FastAPI App Initialization ---
app = FastAPI(
    title="Anita CMS",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=True
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5469" 
    ],
    allow_credentials=True, 
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=[
        "Content-Type",
        "Authorization",
    ],
)

# --- Static Files ---
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static-directory")
app.mount("/uploads", StaticFiles(directory=BASE_DIR / "uploads"), name="uploads-directory")

# --- API Router Organization ---
api_router = APIRouter()

api_router.include_router(admin_route.router, tags=["Admin"])
api_router.include_router(editor_route.router, tags=["Editor"])
api_router.include_router(config_route.router, tags=["Config"])
api_router.include_router(pb_proxy.router, tags=["PB Proxy"])
api_router.include_router(media_route.router, tags=["Media"])
api_router.include_router(file_route.router, tags=["Files"])
api_router.include_router(roles_route.router, tags=["Roles"])
api_router.include_router(pages_route.router, tags=["Pages"]) 
api_router.include_router(auth_route.router, tags=["Authentication"]) 
api_router.include_router(public_route.router, tags=["Public"])   

app.include_router(api_router)


# --- Main Entry Point ---
if __name__ == "__main__":
    # Run the interactive setup (Theme picker & JWT Gen)
    # This blocks until the user finishes setup
    interactive_setup()
    
    # Get port from command-line argument, default to 5469
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5469
    print(f"Starting server on http://127.0.0.1:{port}")
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=False)