"""Infrastructure-related Pydantic schemas."""

from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


class FinalizeRequest(BaseModel):
    """Request to finalize layout and generate infrastructure."""
    
    connection_point: List[float] = Field(
        ..., 
        description="Main utility connection point [x, y]"
    )
    use_steiner: bool = Field(
        default=False, 
        description="Use Steiner tree algorithm (slower but shorter)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "connection_point": [0, 100],
                "use_steiner": False
            }
        }


class InfrastructureLine(BaseModel):
    """Infrastructure line information."""
    
    type: str = Field(..., description="Line type: electric or water")
    id: str = Field(..., description="Line ID (E1, W1, etc.)")
    coordinates: List[List[float]] = Field(..., description="Line coordinates")
    length: float = Field(..., description="Line length in meters")


class FinalizeResponse(BaseModel):
    """Response from finalization with infrastructure."""
    
    success: bool
    electric_lines: List[InfrastructureLine] = Field(default_factory=list)
    water_lines: List[InfrastructureLine] = Field(default_factory=list)
    total_electric_length: float = 0.0
    total_water_length: float = 0.0
    error: Optional[str] = None
    geojson: Optional[dict] = Field(
        default=None, 
        description="Complete infrastructure as GeoJSON"
    )
