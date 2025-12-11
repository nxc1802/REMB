"""
Procedural Generation Project - FastAPI Backend

Generates detailed CAD-ready layouts using procedural techniques:
- L-Systems / Skeletonization for road networks
- OBB Tree / Shape Grammar for lot subdivision  
- Wave Function Collapse for detail placement
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.generation_routes import router as generation_router
from api.routes.dxf_routes import router as dxf_router
from core.config.settings import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    logger.info("Starting Procedural Generation API...")
    yield
    logger.info("Shutting down Procedural Generation API...")


app = FastAPI(
    title="Procedural Generation API",
    description="Generate detailed CAD-ready site layouts using procedural techniques",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if settings.cors_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(generation_router, prefix="/api", tags=["Generation"])
app.include_router(dxf_router, prefix="/api", tags=["DXF"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Procedural Generation API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "generate_roads": "POST /api/generate/roads",
            "generate_subdivision": "POST /api/generate/subdivision",
            "generate_full": "POST /api/generate/full",
            "upload_dxf": "POST /api/upload-dxf"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
