"""DXF upload and processing routes."""

import tempfile
import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from shapely.geometry import Polygon, LineString

from api.schemas.planning import BlockInfo, StateResponse
from core.geometry import extract_blocks, polygon_to_coords, calculate_coverage

router = APIRouter()


@router.post("/upload-dxf", response_model=StateResponse)
async def upload_dxf(
    file: UploadFile = File(...),
    road_width: float = 12.0
):
    """Upload DXF file and extract blocks.
    
    Phase 1: Pre-processing
    
    Args:
        file: DXF file upload
        road_width: Road width for buffering (meters)
    """
    if not file.filename.lower().endswith('.dxf'):
        raise HTTPException(
            status_code=400, 
            detail="File must be a DXF file"
        )
    
    # Read content
    content = await file.read()
    
    # Use robust parser
    from utils.dxf_utils import load_dxf_content
    boundary, roads = load_dxf_content(content)
    
    if boundary is None:
        raise HTTPException(
            status_code=400,
            detail="No closed boundary polygon found in DXF. Ensure the site boundary is a closed polyline."
        )
    
    # Extract blocks
    blocks = extract_blocks(
        boundary=boundary,
        road_network=roads,
        road_width=road_width
    )
    
    # Store in state
    from api.routes.planning_routes import _state
    _state["boundary"] = boundary
    _state["blocks"] = blocks
    
    # Calculate stats
    stats = calculate_coverage(boundary, [])
    
    return StateResponse(
        boundary=polygon_to_coords(boundary),
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


@router.post("/upload-geojson", response_model=StateResponse)
async def upload_geojson(
    file: UploadFile = File(...),
    road_width: float = 12.0
):
    """Upload GeoJSON file with boundary and roads.
    
    Expected format:
    {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"role": "boundary"}, "geometry": {...}},
            {"type": "Feature", "properties": {"role": "road"}, "geometry": {...}}
        ]
    }
    """
    import json
    from shapely.geometry import shape
    
    content = await file.read()
    
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    features = data.get("features", [])
    if not features:
        raise HTTPException(status_code=400, detail="No features in GeoJSON")
    
    boundary = None
    roads = []
    
    for feature in features:
        props = feature.get("properties", {})
        geom = feature.get("geometry")
        
        if not geom:
            continue
        
        role = props.get("role", "").lower()
        geom_type = geom.get("type", "").lower()
        
        if role == "boundary" or (boundary is None and geom_type == "polygon"):
            boundary = shape(geom)
        elif role == "road" or geom_type == "linestring":
            roads.append(shape(geom))
    
    if boundary is None:
        raise HTTPException(
            status_code=400,
            detail="No boundary polygon found in GeoJSON"
        )
    
    # Extract blocks
    blocks = extract_blocks(
        boundary=boundary,
        road_network=roads,
        road_width=road_width
    )
    
    # Store in state
    from api.routes.planning_routes import _state
    _state["boundary"] = boundary
    _state["blocks"] = blocks
    
    # Calculate stats
    stats = calculate_coverage(boundary, [])
    
    return StateResponse(
        boundary=polygon_to_coords(boundary),
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
