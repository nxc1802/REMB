"""Configuration settings for Procedural Generation."""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # API
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class RoadNetworkSettings(BaseSettings):
    """Settings for road network generation."""
    
    # L-Systems
    lsystem_iterations: int = 3
    lsystem_step_length: float = 50.0  # meters
    lsystem_angle: float = 30.0  # degrees
    lsystem_length_decay: float = 0.8
    
    # Skeletonization
    skeleton_resolution: float = 1.0  # m/pixel
    skeleton_min_road_length: float = 50.0  # meters
    
    # Road smoothing
    fillet_radius: float = 12.0  # R=12m for container trucks
    road_width_main: float = 12.0  # meters
    road_width_secondary: float = 8.0  # meters


class SubdivisionSettings(BaseSettings):
    """Settings for lot subdivision."""
    
    # OBB Tree
    min_lot_area: float = 1000.0  # m²
    max_lot_area: float = 10000.0  # m²
    max_tree_depth: int = 5
    aspect_ratio_limit: float = 4.0
    
    # Shape Grammar
    setback_front: float = 3.0  # meters
    setback_side: float = 2.0  # meters
    
    # Lot dimensions
    target_lot_width: float = 40.0  # meters
    min_lot_width: float = 20.0  # meters
    max_lot_width: float = 80.0  # meters


class TileSystemSettings(BaseSettings):
    """Settings for Wave Function Collapse."""
    
    # Grid
    default_tile_size: float = 10.0  # meters
    adaptive_tile_min: float = 5.0  # meters
    adaptive_tile_max: float = 50.0  # meters
    
    # WFC
    wfc_max_iterations: int = 10000
    wfc_backtrack_limit: int = 100


class PostProcessingSettings(BaseSettings):
    """Settings for post-processing."""
    
    # Buffers
    sidewalk_width: float = 2.0  # meters
    green_buffer_width: float = 5.0  # meters
    separation_width: float = 3.0  # meters


class QualitySettings(BaseSettings):
    """Quality validation settings (from shape_quality.py)."""
    
    min_rectangularity: float = 0.75
    max_aspect_ratio: float = 4.0
    min_area: float = 1000.0  # m²


# Default instances
settings = Settings()
road_settings = RoadNetworkSettings()
subdivision_settings = SubdivisionSettings()
tile_settings = TileSystemSettings()
postprocess_settings = PostProcessingSettings()
quality_settings = QualitySettings()


# Combined defaults for pipeline
DEFAULT_SETTINGS = {
    "road": road_settings,
    "subdivision": subdivision_settings,
    "tile": tile_settings,
    "postprocess": postprocess_settings,
    "quality": quality_settings
}
