"""Infrastructure-related Pydantic schemas."""

from typing import List, Optional, Tuple, Dict, Any
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
    # Enhanced options
    use_enhanced: bool = Field(
        default=True,
        description="Use enhanced routing with loop network, transformers, drainage"
    )
    use_loop_network: bool = Field(
        default=True,
        description="Add redundant edges for electrical network reliability"
    )
    redundancy_ratio: float = Field(
        default=0.15,
        description="Ratio of extra edges to add (0.0-1.0)"
    )
    add_transformers: bool = Field(
        default=True,
        description="Calculate optimal transformer positions"
    )
    add_drainage: bool = Field(
        default=True,
        description="Calculate drainage flow directions"
    )
    drainage_outlet: Optional[List[float]] = Field(
        default=None,
        description="Drainage outlet point [x, y] (defaults to connection_point)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "connection_point": [0, 100],
                "use_enhanced": True,
                "use_loop_network": True,
                "add_transformers": True,
                "add_drainage": True
            }
        }


class InfrastructureLine(BaseModel):
    """Infrastructure line information."""
    
    type: str = Field(..., description="Line type: electric or water")
    id: str = Field(..., description="Line ID (E1, W1, etc.)")
    coordinates: List[List[float]] = Field(..., description="Line coordinates")
    length: float = Field(..., description="Line length in meters")


class TransformerPoint(BaseModel):
    """Transformer station location."""
    id: str
    coordinates: List[float]


class DrainageArrow(BaseModel):
    """Drainage flow direction arrow."""
    id: str
    start: List[float]
    end: List[float]


class FinalizeResponse(BaseModel):
    """Response from finalization with infrastructure."""
    
    success: bool
    electric_lines: List[InfrastructureLine] = Field(default_factory=list)
    water_lines: List[InfrastructureLine] = Field(default_factory=list)
    total_electric_length: float = 0.0
    total_water_length: float = 0.0
    # Enhanced fields
    transformers: List[TransformerPoint] = Field(default_factory=list)
    drainage_arrows: List[DrainageArrow] = Field(default_factory=list)
    redundant_edges: int = 0
    error: Optional[str] = None
    geojson: Optional[dict] = Field(
        default=None, 
        description="Complete infrastructure as GeoJSON"
    )
