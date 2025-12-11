"""Request schemas for Procedural Generation API."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    """GeoJSON-style coordinates."""
    type: str = "Polygon"
    coordinates: List[List[List[float]]] = Field(
        ..., 
        description="Polygon coordinates [[[x1,y1], [x2,y2], ...]]"
    )
    properties: Optional[Dict[str, Any]] = None


class RoadNetworkConfig(BaseModel):
    """Configuration for road network generation."""
    algorithm: str = Field(
        default="skeleton",
        description="Algorithm: 'skeleton', 'l_systems', or 'hybrid'"
    )
    fillet_radius: float = Field(default=12.0, ge=0, description="Corner fillet radius (m)")
    road_width_main: float = Field(default=12.0, ge=4, description="Main road width (m)")
    road_width_secondary: float = Field(default=8.0, ge=3, description="Secondary road width (m)")
    
    # L-Systems specific
    lsystem_iterations: int = Field(default=3, ge=1, le=6)
    lsystem_angle: float = Field(default=30.0, ge=10, le=90)
    
    # Skeleton specific  
    skeleton_resolution: float = Field(default=1.0, ge=0.5, le=5.0)


class SubdivisionConfig(BaseModel):
    """Configuration for lot subdivision."""
    min_lot_area: float = Field(default=1000.0, ge=100, description="Min lot area (m²)")
    max_lot_area: float = Field(default=10000.0, ge=500, description="Max lot area (m²)")
    target_lot_width: float = Field(default=40.0, ge=10, description="Target lot width (m)")
    min_lot_width: float = Field(default=20.0, ge=5, description="Min lot width (m)")
    max_lot_width: float = Field(default=80.0, ge=20, description="Max lot width (m)")
    max_tree_depth: int = Field(default=5, ge=1, le=10)
    setback_front: float = Field(default=3.0, ge=0, description="Front setback (m)")
    setback_side: float = Field(default=2.0, ge=0, description="Side setback (m)")


class TileSystemConfig(BaseModel):
    """Configuration for WFC tile placement."""
    enabled: bool = Field(default=True, description="Enable WFC tile placement")
    tile_size: float = Field(default=10.0, ge=5, le=100, description="Tile size (m)")
    adaptive_sizing: bool = Field(default=True, description="Auto-adjust tile size")
    tile_set: str = Field(default="industrial", description="Tile set to use")


class PostProcessingConfig(BaseModel):
    """Configuration for post-processing."""
    sidewalk_width: float = Field(default=2.0, ge=0, description="Sidewalk width (m)")
    green_buffer_width: float = Field(default=5.0, ge=0, description="Green buffer (m)")
    smooth_corners: bool = Field(default=True, description="Apply corner smoothing")


class QualityConfig(BaseModel):
    """Quality validation settings."""
    min_rectangularity: float = Field(default=0.75, ge=0.5, le=1.0)
    max_aspect_ratio: float = Field(default=4.0, ge=1.0, le=10.0)
    convert_invalid_to_green: bool = Field(default=True)


# === Request Models ===

class RoadGenerationRequest(BaseModel):
    """Request for road network generation."""
    site_boundary: Coordinates
    config: Optional[RoadNetworkConfig] = None


class SubdivisionRequest(BaseModel):
    """Request for lot subdivision."""
    site_boundary: Coordinates
    roads: Optional[List[List[List[float]]]] = Field(
        default=None,
        description="Optional pre-computed road lines"
    )
    config: Optional[SubdivisionConfig] = None


class FullPipelineRequest(BaseModel):
    """Request for full procedural generation pipeline."""
    site_boundary: Coordinates
    
    road_config: Optional[RoadNetworkConfig] = None
    subdivision_config: Optional[SubdivisionConfig] = None
    tile_config: Optional[TileSystemConfig] = None
    postprocess_config: Optional[PostProcessingConfig] = None
    quality_config: Optional[QualityConfig] = None
    
    # Pipeline control
    stages: List[str] = Field(
        default=["roads", "subdivision", "postprocess"],
        description="Stages to run: roads, subdivision, tiles, postprocess"
    )
