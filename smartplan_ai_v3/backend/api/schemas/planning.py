"""Planning-related Pydantic schemas."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AssetInfo(BaseModel):
    """Asset information."""
    
    type: str = Field(..., description="Asset type keyword")
    polygon: List[List[float]] = Field(..., description="Polygon coordinates")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "factory_standard",
                "polygon": [[0, 0], [100, 0], [100, 50], [0, 50], [0, 0]]
            }
        }


class BlockInfo(BaseModel):
    """Block information."""
    
    id: str = Field(..., description="Block ID (B1, B2, etc.)")
    polygon: List[List[float]] = Field(..., description="Boundary coordinates")
    area: float = Field(..., description="Area in m²")
    assets: List[AssetInfo] = Field(default_factory=list, description="Placed assets")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "B1",
                "polygon": [[0, 0], [200, 0], [200, 150], [0, 150], [0, 0]],
                "area": 30000.0,
                "assets": []
            }
        }


class GenerateRequest(BaseModel):
    """Request to generate assets for a block."""
    
    block_id: str = Field(..., description="Target block ID")
    user_request: str = Field(..., description="Natural language request")
    
    class Config:
        json_schema_extra = {
            "example": {
                "block_id": "B1",
                "user_request": "Thêm 2 nhà kho lạnh vào khu đất"
            }
        }


class GenerateResponse(BaseModel):
    """Response from asset generation."""
    
    success: bool
    action: str = "add"  # add, clear, replace
    new_assets: List[AssetInfo] = Field(default_factory=list)
    explanation: str = ""
    error: Optional[str] = None


class ValidateRequest(BaseModel):
    """Request to validate proposed assets."""
    
    block_id: str = Field(..., description="Target block ID")
    new_assets: List[AssetInfo] = Field(..., description="Assets to validate")


class ValidateResponse(BaseModel):
    """Response from validation."""
    
    success: bool
    merged_assets: List[AssetInfo] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class BoundaryInput(BaseModel):
    """Input for setting boundary."""
    
    boundary: List[List[float]] = Field(..., description="Boundary coordinates")
    roads: Optional[List[Dict[str, Any]]] = Field(
        default=None, 
        description="Road GeoJSON features"
    )
    road_width: float = Field(default=12.0, description="Road width in meters")


class StateResponse(BaseModel):
    """Response with current planning state."""
    
    boundary: Optional[List[List[float]]] = None
    blocks: List[BlockInfo] = Field(default_factory=list)
    total_area: float = 0.0
    used_area: float = 0.0
    coverage_ratio: float = 0.0
