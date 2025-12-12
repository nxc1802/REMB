"""Planning API routes for block and asset management."""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from shapely.geometry import Polygon

from api.schemas.planning import (
    BlockInfo,
    AssetInfo,
    GenerateRequest,
    GenerateResponse,
    ValidateRequest,
    ValidateResponse,
    BoundaryInput,
    StateResponse,
)
from core.geometry import (
    coords_to_polygon,
    polygon_to_coords,
    extract_blocks,
    validate_and_merge,
    calculate_coverage,
)
from core.llm import SpatialPlannerAgent

router = APIRouter()

# Global state (in production, use database)
_state: Dict[str, Any] = {
    "boundary": None,
    "blocks": [],
    "agent": None,
}


def _get_agent() -> SpatialPlannerAgent:
    """Get or create agent instance."""
    if _state["agent"] is None:
        _state["agent"] = SpatialPlannerAgent()
    return _state["agent"]


@router.post("/set-boundary", response_model=StateResponse)
async def set_boundary(input_data: BoundaryInput):
    """Set site boundary and extract blocks.
    
    Phase 1: Pre-processing
    """
    # Parse boundary
    boundary = coords_to_polygon(input_data.boundary)
    if boundary is None or boundary.is_empty:
        raise HTTPException(status_code=400, detail="Invalid boundary coordinates")
    
    _state["boundary"] = boundary
    
    # Parse roads if provided
    roads = []
    if input_data.roads:
        from shapely.geometry import LineString, shape
        for road_feature in input_data.roads:
            geom = road_feature.get("geometry", road_feature)
            if geom.get("type") == "LineString":
                coords = geom.get("coordinates", [])
                if coords:
                    roads.append(LineString(coords))
    
    # Extract blocks
    blocks = extract_blocks(
        boundary=boundary,
        road_network=roads,
        road_width=input_data.road_width
    )
    
    _state["blocks"] = blocks
    
    # Calculate stats
    stats = calculate_coverage(boundary, [])
    
    return StateResponse(
        boundary=input_data.boundary,
        blocks=[
            BlockInfo(
                id=b.id,
                polygon=polygon_to_coords(b.polygon),
                area=b.area,
                assets=[]
            )
            for b in blocks
        ],
        total_area=stats["total_area"],
        used_area=stats["used_area"],
        coverage_ratio=stats["coverage_ratio"]
    )


@router.get("/blocks", response_model=list[BlockInfo])
async def list_blocks():
    """List all extracted blocks."""
    return [
        BlockInfo(
            id=b.id,
            polygon=polygon_to_coords(b.polygon),
            area=b.area,
            assets=[
                AssetInfo(type=a["type"], polygon=a["polygon"])
                for a in b.assets
            ]
        )
        for b in _state["blocks"]
    ]


@router.get("/blocks/{block_id}", response_model=BlockInfo)
async def get_block(block_id: str):
    """Get specific block details."""
    for block in _state["blocks"]:
        if block.id == block_id:
            return BlockInfo(
                id=block.id,
                polygon=polygon_to_coords(block.polygon),
                area=block.area,
                assets=[
                    AssetInfo(type=a["type"], polygon=a["polygon"])
                    for a in block.assets
                ]
            )
    
    raise HTTPException(status_code=404, detail=f"Block {block_id} not found")


@router.post("/blocks/{block_id}/generate", response_model=GenerateResponse)
async def generate_assets(block_id: str, request: GenerateRequest):
    """Generate assets for a block using LLM.
    
    Phase 2: Generative Design
    """
    # Find block
    block = None
    for b in _state["blocks"]:
        if b.id == block_id:
            block = b
            break
    
    if block is None:
        raise HTTPException(status_code=404, detail=f"Block {block_id} not found")
    
    # Get agent
    agent = _get_agent()
    
    # Generate assets
    boundary_coords = polygon_to_coords(block.polygon)
    result = agent.generate_assets(
        boundary_coords=boundary_coords,
        existing_assets=block.assets,
        user_request=request.user_request
    )
    
    if not result.success:
        return GenerateResponse(
            success=False,
            action="add",
            error=result.error
        )
    
    return GenerateResponse(
        success=True,
        action=result.action,
        new_assets=[
            AssetInfo(type=a["type"], polygon=a["polygon"])
            for a in result.new_assets
        ],
        explanation=result.explanation
    )


@router.post("/validate", response_model=ValidateResponse)
async def validate_assets(request: ValidateRequest):
    """Validate proposed assets.
    
    Phase 3: Validation (Gatekeeper)
    """
    # Find block
    block = None
    for b in _state["blocks"]:
        if b.id == request.block_id:
            block = b
            break
    
    if block is None:
        raise HTTPException(
            status_code=404, 
            detail=f"Block {request.block_id} not found"
        )
    
    # Convert new assets to dict format
    new_assets = [
        {"type": a.type, "polygon": a.polygon}
        for a in request.new_assets
    ]
    
    # Run validation
    result = validate_and_merge(
        boundary=block.polygon,
        existing_assets=block.assets,
        new_assets=new_assets
    )
    
    if result.success:
        # Update block with merged assets
        block.assets = result.merged_assets
    
    return ValidateResponse(
        success=result.success,
        merged_assets=[
            AssetInfo(type=a["type"], polygon=a["polygon"])
            for a in result.merged_assets
        ],
        errors=result.errors,
        warnings=result.warnings
    )


@router.get("/state", response_model=StateResponse)
async def get_state():
    """Get current planning state."""
    boundary = _state.get("boundary")
    blocks = _state.get("blocks", [])
    
    # Collect all assets
    all_assets = []
    for block in blocks:
        all_assets.extend(block.assets)
    
    # Calculate stats
    stats = calculate_coverage(boundary, all_assets) if boundary else {
        "total_area": 0, "used_area": 0, "coverage_ratio": 0
    }
    
    return StateResponse(
        boundary=polygon_to_coords(boundary) if boundary else None,
        blocks=[
            BlockInfo(
                id=b.id,
                polygon=polygon_to_coords(b.polygon),
                area=b.area,
                assets=[
                    AssetInfo(type=a["type"], polygon=a["polygon"])
                    for a in b.assets
                ]
            )
            for b in blocks
        ],
        total_area=stats["total_area"],
        used_area=stats["used_area"],
        coverage_ratio=stats["coverage_ratio"]
    )


@router.delete("/blocks/{block_id}/assets")
async def clear_block_assets(block_id: str):
    """Clear all assets from a block."""
    for block in _state["blocks"]:
        if block.id == block_id:
            cleared_count = len(block.assets)
            block.assets = []
            return {"status": "cleared", "block_id": block_id, "cleared_count": cleared_count}
    
    raise HTTPException(status_code=404, detail=f"Block {block_id} not found")


@router.delete("/blocks/{block_id}/assets/{asset_index}")
async def delete_asset(block_id: str, asset_index: int):
    """Delete a specific asset by index from a block."""
    for block in _state["blocks"]:
        if block.id == block_id:
            if 0 <= asset_index < len(block.assets):
                deleted_asset = block.assets.pop(asset_index)
                return {
                    "status": "deleted",
                    "block_id": block_id,
                    "asset_index": asset_index,
                    "deleted_type": deleted_asset.get("type", "unknown")
                }
            else:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Asset index {asset_index} out of range (0-{len(block.assets)-1})"
                )
    
    raise HTTPException(status_code=404, detail=f"Block {block_id} not found")


@router.delete("/reset")
async def reset_state():
    """Reset planning state."""
    _state["boundary"] = None
    _state["blocks"] = []
    return {"status": "reset"}


@router.get("/models")
async def list_models():
    """List available LLM models."""
    agent = _get_agent()
    return {
        "current_provider": agent.provider,
        "current_model": agent.model_name,
        "providers": agent.PROVIDERS
    }


@router.post("/models/switch")
async def switch_model(provider: str, model: str):
    """Switch to a different LLM model."""
    agent = _get_agent()
    if provider not in agent.PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    if model not in agent.PROVIDERS[provider].get("models", []):
        raise HTTPException(status_code=400, detail=f"Unknown model: {model}")
    
    agent.set_model(provider, model)
    return {
        "status": "switched",
        "provider": provider,
        "model": model
    }


@router.get("/export/json")
async def export_json():
    """Export current state as JSON."""
    boundary = _state.get("boundary")
    blocks = _state.get("blocks", [])
    
    return {
        "boundary": polygon_to_coords(boundary) if boundary else None,
        "blocks": [
            {
                "id": b.id,
                "polygon": polygon_to_coords(b.polygon),
                "area": b.area,
                "assets": b.assets
            }
            for b in blocks
        ]
    }


@router.get("/export/geojson")
async def export_geojson():
    """Export current state as GeoJSON FeatureCollection."""
    boundary = _state.get("boundary")
    blocks = _state.get("blocks", [])
    
    features = []
    
    # Add boundary feature
    if boundary:
        features.append({
            "type": "Feature",
            "properties": {"role": "boundary", "area": boundary.area},
            "geometry": {
                "type": "Polygon",
                "coordinates": [polygon_to_coords(boundary)]
            }
        })
    
    # Add block and asset features
    for block in blocks:
        features.append({
            "type": "Feature",
            "properties": {"role": "block", "id": block.id, "area": block.area},
            "geometry": {
                "type": "Polygon",
                "coordinates": [polygon_to_coords(block.polygon)]
            }
        })
        
        for idx, asset in enumerate(block.assets):
            features.append({
                "type": "Feature",
                "properties": {
                    "role": "asset",
                    "type": asset.get("type", "unknown"),
                    "block_id": block.id,
                    "index": idx
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [asset.get("polygon", [])]
                }
            })
    
    return {
        "type": "FeatureCollection",
        "name": "SmartPlan_AI_v3_Output",
        "features": features
    }
