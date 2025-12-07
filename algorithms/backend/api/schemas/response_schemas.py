"""Response schemas for the API."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class StageResult(BaseModel):
    """Result from a single optimization stage."""
    
    stage_name: str = Field(..., description="Name of the stage")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON geometry of results")
    metrics: Dict[str, float] = Field(..., description="Performance metrics")
    parameters: Dict[str, Any] = Field(..., description="Parameters used")


class OptimizationResponse(BaseModel):
    """Response model containing optimization results."""
    
    success: bool = Field(..., description="Whether optimization succeeded")
    message: str = Field(..., description="Status message")
    stages: List[StageResult] = Field(default=[], description="Results from each stage")
    final_layout: Optional[Dict[str, Any]] = Field(None, description="Final GeoJSON layout")
    total_lots: Optional[int] = Field(None, description="Total number of lots created")
    statistics: Optional[Dict[str, Any]] = Field(None, description="Overall statistics")


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(default="healthy", description="Service status")
    version: str = Field(default="1.0.0", description="API version")
