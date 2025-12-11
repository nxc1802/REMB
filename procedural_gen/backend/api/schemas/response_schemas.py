"""Response schemas for Procedural Generation API."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class GeoJSONFeature(BaseModel):
    """GeoJSON Feature."""
    type: str = "Feature"
    geometry: Dict[str, Any]
    properties: Optional[Dict[str, Any]] = None


class GeoJSONFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection."""
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]


class StageResult(BaseModel):
    """Result from a single pipeline stage."""
    stage_name: str
    success: bool
    duration_ms: float
    item_count: int
    geojson: Optional[GeoJSONFeatureCollection] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class RoadGenerationResponse(BaseModel):
    """Response from road generation endpoint."""
    success: bool
    roads: GeoJSONFeatureCollection
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional info: total_length, road_count, algorithm"
    )
    duration_ms: float


class SubdivisionResponse(BaseModel):
    """Response from subdivision endpoint."""
    success: bool
    lots: GeoJSONFeatureCollection
    green_spaces: Optional[GeoJSONFeatureCollection] = None
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional info: lot_count, total_area, quality_stats"
    )
    duration_ms: float


class FullPipelineResponse(BaseModel):
    """Response from full pipeline endpoint."""
    success: bool
    stages: List[StageResult]
    
    # Final outputs
    roads: Optional[GeoJSONFeatureCollection] = None
    lots: Optional[GeoJSONFeatureCollection] = None
    sidewalks: Optional[GeoJSONFeatureCollection] = None
    green_spaces: Optional[GeoJSONFeatureCollection] = None
    tiles: Optional[GeoJSONFeatureCollection] = None
    
    # Aggregated metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary statistics and configuration used"
    )
    total_duration_ms: float


class ErrorResponse(BaseModel):
    """Error response."""
    success: bool = False
    error: str
    detail: Optional[str] = None
    stage: Optional[str] = None
