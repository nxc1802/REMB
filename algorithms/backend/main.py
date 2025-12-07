"""FastAPI application entry point."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.schemas.response_schemas import HealthResponse
from api.routes import optim_router, dxf_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Land Redistribution Algorithm API",
    description="API for testing land subdivision and redistribution algorithms",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(optim_router, prefix="/api")
app.include_router(dxf_router, prefix="/api")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy", version="2.0.0")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Land Redistribution Algorithm API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.on_event("startup")
async def startup_event():
    """Log startup information."""
    logger.info("Land Redistribution API started (v2.0.0 - Modular Architecture)")
