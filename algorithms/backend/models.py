"""Pydantic models for API request/response schemas."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class AlgorithmConfig(BaseModel):
    """Configuration parameters for the land redistribution algorithm."""
    
    # Stage 1: Grid optimization parameters
    spacing_min: float = Field(default=20.0, ge=10.0, le=50.0, description="Minimum grid spacing in meters")
    spacing_max: float = Field(default=30.0, ge=10.0, le=50.0, description="Maximum grid spacing in meters")
    angle_min: float = Field(default=0.0, ge=0.0, le=90.0, description="Minimum grid angle in degrees")
    angle_max: float = Field(default=90.0, ge=0.0, le=90.0, description="Maximum grid angle in degrees")
    
    # Stage 2: Subdivision parameters (Industrial lots)
    min_lot_width: float = Field(default=20.0, ge=10.0, le=40.0, description="Minimum lot width in meters")
    max_lot_width: float = Field(default=80.0, ge=40.0, le=120.0, description="Maximum lot width in meters")
    target_lot_width: float = Field(default=40.0, ge=20.0, le=100.0, description="Target lot width in meters")
    
    # Infrastructure parameters
    road_width: float = Field(default=6.0, ge=3.0, le=10.0, description="Road width in meters")
    block_depth: float = Field(default=50.0, ge=30.0, le=100.0, description="Block depth in meters")
    
    # Optimization parameters
    population_size: int = Field(default=50, ge=20, le=200, description="NSGA-II population size")
    generations: int = Field(default=100, ge=50, le=500, description="Number of generations")
    ortools_time_limit: float = Field(default=5.0, ge=0.1, le=60.0, description="OR-Tools solver time limit per block (seconds)")


class LandPlot(BaseModel):
    """A land plot represented as a GeoJSON polygon."""
    
    type: str = Field(default="Polygon", description="Geometry type")
    coordinates: List[List[List[float]]] = Field(..., description="Polygon coordinates [[x, y], ...]")
    properties: Optional[Dict[str, Any]] = Field(default={}, description="Additional properties")


class OptimizationRequest(BaseModel):
    """Request model for running the optimization algorithm."""
    
    config: AlgorithmConfig = Field(..., description="Algorithm configuration")
    land_plots: List[LandPlot] = Field(..., description="Initial land plots to subdivide")


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
