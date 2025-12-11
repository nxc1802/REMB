"""SmartPlan AI - FastAPI Backend.

LLM-driven conversational design for industrial park planning.
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
    logger.info("SmartPlan AI starting up...")
    yield
    logger.info("SmartPlan AI shutting down...")


# Create FastAPI app
app = FastAPI(
    title="SmartPlan AI",
    description="LLM-driven conversational design for industrial park planning",
    version="1.0.0",
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
from api.routes import design_routes, chat_routes, dxf_routes

app.include_router(design_routes.router, prefix="/api", tags=["Design"])
app.include_router(chat_routes.router, prefix="/api", tags=["Chat"])
app.include_router(dxf_routes.router, prefix="/api", tags=["DXF"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0", "service": "SmartPlan AI"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "SmartPlan AI",
        "description": "Design by Conversation",
        "docs": "/docs"
    }
