"""
FastAPI Main Application - REMB Optimization Engine
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import logging

from config.settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-Powered Industrial Estate Master Planning Optimization Engine"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API
class OptimizationRequest(BaseModel):
    """Request model for optimization"""
    site_id: str
    population_size: int = 100
    n_generations: int = 200
    n_plots: int = 20


class OptimizationResponse(BaseModel):
    """Response model for optimization"""
    optimization_id: str
    status: str
    n_solutions: int
    generation_time_seconds: float


class LayoutMetricsResponse(BaseModel):
    """Layout metrics response"""
    layout_id: str
    total_area_sqm: float
    sellable_area_sqm: float
    green_space_area_sqm: float
    sellable_ratio: float
    green_space_ratio: float
    is_compliant: bool


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "REMB Industrial Estate Master Planning Optimization Engine",
        "version": settings.VERSION,
        "status": "operational"
    }


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION
    }


@app.post("/api/v1/sites/upload")
async def upload_site_boundary(file: UploadFile = File(...)):
    """
    Upload site boundary file (Shapefile or DXF)
    
    Args:
        file: Shapefile (.shp) or DXF file
        
    Returns:
        Site ID and metadata
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Check file extension
    extension = file.filename.split('.')[-1].lower()
    if f".{extension}" not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type .{extension} not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}"
        )
    
    # TODO: Implement actual file processing
    site_id = "site_123"  # Placeholder
    
    return {
        "site_id": site_id,
        "filename": file.filename,
        "status": "uploaded",
        "message": "Site boundary uploaded successfully"
    }


@app.post("/api/v1/sites/{site_id}/optimize", response_model=OptimizationResponse)
async def optimize_site(site_id: str, request: OptimizationRequest):
    """
    Run optimization for a site
    
    Args:
        site_id: Site identifier
        request: Optimization parameters
        
    Returns:
        Optimization results with Pareto front
    """
    logger.info(f"Starting optimization for site {site_id}")
    
    # TODO: Implement actual optimization
    # This would call NSGA2Optimizer and return results
    
    return OptimizationResponse(
        optimization_id="opt_123",
        status="completed",
        n_solutions=8,
        generation_time_seconds=120.5
    )


@app.get("/api/v1/layouts/{layout_id}/metrics", response_model=LayoutMetricsResponse)
async def get_layout_metrics(layout_id: str):
    """
    Get metrics for a specific layout
    
    Args:
        layout_id: Layout identifier
        
    Returns:
        Layout metrics
    """
    # TODO: Retrieve from database
    return LayoutMetricsResponse(
        layout_id=layout_id,
        total_area_sqm=250000.0,
        sellable_area_sqm=162500.0,
        green_space_area_sqm=37500.0,
        sellable_ratio=0.65,
        green_space_ratio=0.15,
        is_compliant=True
    )


@app.get("/api/v1/layouts/{layout_id}/export")
async def export_layout_dxf(layout_id: str):
    """
    Export layout as DXF file
    
    Args:
        layout_id: Layout identifier
        
    Returns:
        DXF file download
    """
    # TODO: Implement DXF export
    return {
        "layout_id": layout_id,
        "status": "exported",
        "download_url": f"/downloads/{layout_id}.dxf"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
