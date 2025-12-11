"""SmartPlan AI v3.0 - FastAPI Backend.

Automated Industrial Park Planning Engine with LLM-driven spatial design.
"""

import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)
    print(f"✅ Loaded .env from {env_path}")
else:
    print(f"⚠️ No .env file found at {env_path}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("SmartPlan AI v3.0 starting up...")
    logger.info(f"GOOGLE_API_KEY: {'set' if os.environ.get('GOOGLE_API_KEY') else 'not set'}")
    yield
    logger.info("SmartPlan AI v3.0 shutting down...")


# Create FastAPI app
app = FastAPI(
    title="SmartPlan AI v3.0",
    description="Automated Industrial Park Planning Engine with LLM-driven spatial design",
    version="3.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from api.routes import planning_routes, dxf_routes, infrastructure_routes

app.include_router(planning_routes.router, prefix="/api", tags=["Planning"])
app.include_router(dxf_routes.router, prefix="/api", tags=["DXF"])
app.include_router(infrastructure_routes.router, prefix="/api", tags=["Infrastructure"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "3.0.0",
        "service": "SmartPlan AI v3.0"
    }


@app.get("/")
async def root():
    """Root endpoint with API documentation."""
    return {
        "name": "SmartPlan AI v3.0",
        "description": "Automated Industrial Park Planning Engine",
        "docs": "/docs",
        "endpoints": {
            "set_boundary": "POST /api/set-boundary",
            "upload_dxf": "POST /api/upload-dxf",
            "list_blocks": "GET /api/blocks",
            "generate_assets": "POST /api/blocks/{id}/generate",
            "validate_assets": "POST /api/validate",
            "finalize": "POST /api/finalize",
            "get_state": "GET /api/state"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
