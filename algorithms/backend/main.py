"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import router
from models import HealthResponse

app = FastAPI(
    title="Land Redistribution Algorithm API",
    description="API for testing land subdivision and redistribution algorithms",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy", version="1.0.0")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Land Redistribution Algorithm API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }
