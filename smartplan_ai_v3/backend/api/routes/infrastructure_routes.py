"""Infrastructure routing API routes."""

from fastapi import APIRouter, HTTPException
from shapely.geometry import mapping

from api.schemas.infrastructure import (
    FinalizeRequest,
    FinalizeResponse,
    InfrastructureLine,
    TransformerPoint,
    DrainageArrow,
)
from core.geometry import polygon_to_coords
from core.infrastructure import route_utilities, route_utilities_enhanced

router = APIRouter()


@router.post("/finalize", response_model=FinalizeResponse)
async def finalize_layout(request: FinalizeRequest):
    """Finalize layout and generate infrastructure routing.
    
    Phase 4: Infrastructure Routing
    
    Runs MST/Steiner Tree algorithm to connect all assets
    to the main utility connection point.
    
    Enhanced mode adds:
    - Loop network for electrical reliability (15% redundant edges)
    - K-Means transformer placement
    - Gravity-based drainage flow
    """
    from api.routes.planning_routes import _state
    
    blocks = _state.get("blocks", [])
    boundary = _state.get("boundary")
    
    if not blocks:
        raise HTTPException(
            status_code=400,
            detail="No blocks available. Upload a DXF or set boundary first."
        )
    
    # Collect all assets from all blocks
    all_assets = []
    for block in blocks:
        all_assets.extend(block.assets)
    
    if not all_assets:
        raise HTTPException(
            status_code=400,
            detail="No assets placed. Generate and validate assets first."
        )
    
    # Route utilities
    connection_point = tuple(request.connection_point)
    
    if request.use_enhanced:
        # Use enhanced routing with loop network, transformers, drainage
        drainage_outlet = tuple(request.drainage_outlet) if request.drainage_outlet else None
        
        result = route_utilities_enhanced(
            assets=all_assets,
            connection_point=connection_point,
            boundary=boundary,
            use_loop_network=request.use_loop_network,
            redundancy_ratio=request.redundancy_ratio,
            add_transformers=request.add_transformers,
            add_drainage=request.add_drainage,
            drainage_outlet=drainage_outlet
        )
    else:
        # Use basic MST/Steiner routing
        result = route_utilities(
            assets=all_assets,
            connection_point=connection_point,
            boundary=boundary,
            use_steiner=request.use_steiner
        )
    
    if not result.success:
        return FinalizeResponse(
            success=False,
            error=result.error
        )
    
    # Convert LineStrings to response format
    electric_lines = []
    for i, line in enumerate(result.electric_lines):
        coords = list(line.coords)
        electric_lines.append(InfrastructureLine(
            type="electric",
            id=f"E{i+1}",
            coordinates=[[c[0], c[1]] for c in coords],
            length=line.length
        ))
    
    water_lines = []
    for i, line in enumerate(result.water_lines):
        coords = list(line.coords)
        water_lines.append(InfrastructureLine(
            type="water",
            id=f"W{i+1}",
            coordinates=[[c[0], c[1]] for c in coords],
            length=line.length
        ))
    
    # Convert transformers
    transformers = []
    for i, pos in enumerate(result.transformers):
        transformers.append(TransformerPoint(
            id=f"T{i+1}",
            coordinates=[pos[0], pos[1]]
        ))
    
    # Convert drainage arrows
    drainage_arrows = []
    for i, arrow in enumerate(result.drainage_arrows):
        drainage_arrows.append(DrainageArrow(
            id=f"D{i+1}",
            start=[arrow['start'][0], arrow['start'][1]],
            end=[arrow['end'][0], arrow['end'][1]]
        ))
    
    return FinalizeResponse(
        success=True,
        electric_lines=electric_lines,
        water_lines=water_lines,
        total_electric_length=result.total_electric_length,
        total_water_length=result.total_water_length,
        transformers=transformers,
        drainage_arrows=drainage_arrows,
        redundant_edges=result.redundant_edges,
        geojson=result.to_geojson()
    )


@router.get("/infrastructure")
async def get_infrastructure():
    """Get current infrastructure routing if available."""
    # TODO: Store infrastructure result in state
    return {"message": "Run /finalize first to generate infrastructure"}
