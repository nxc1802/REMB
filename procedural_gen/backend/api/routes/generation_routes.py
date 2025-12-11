"""Generation API routes for procedural layout creation."""

import time
import logging
import traceback
from typing import List

from fastapi import APIRouter, HTTPException
from shapely.geometry import Polygon, mapping, LineString

from api.schemas.request_schemas import (
    RoadGenerationRequest,
    SubdivisionRequest,
    FullPipelineRequest
)
from api.schemas.response_schemas import (
    RoadGenerationResponse,
    SubdivisionResponse,
    FullPipelineResponse,
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    StageResult,
    ErrorResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()


def coords_to_polygon(coordinates: List[List[List[float]]]) -> Polygon:
    """Convert GeoJSON coordinates to Shapely Polygon."""
    if not coordinates or not coordinates[0]:
        raise ValueError("Invalid coordinates")
    return Polygon(coordinates[0])


def polygon_to_geojson_feature(
    poly: Polygon, 
    properties: dict = None
) -> GeoJSONFeature:
    """Convert Shapely Polygon to GeoJSON Feature."""
    return GeoJSONFeature(
        type="Feature",
        geometry=mapping(poly),
        properties=properties or {}
    )


def linestring_to_geojson_feature(
    line: LineString,
    properties: dict = None
) -> GeoJSONFeature:
    """Convert Shapely LineString to GeoJSON Feature."""
    return GeoJSONFeature(
        type="Feature",
        geometry=mapping(line),
        properties=properties or {}
    )


@router.post("/generate/roads", response_model=RoadGenerationResponse)
async def generate_roads(request: RoadGenerationRequest):
    """Generate road network for the site.
    
    Algorithms:
    - skeleton: Medial axis transform for central main roads
    - l_systems: L-Systems for organic branching patterns
    - hybrid: Skeleton for main + L-Systems for secondary
    """
    start_time = time.time()
    
    try:
        # Parse site boundary
        site = coords_to_polygon(request.site_boundary.coordinates)
        config = request.config or {}
        
        # Import generators (lazy import to avoid circular deps)
        from core.road_network import generate_road_network
        
        algorithm = config.algorithm if hasattr(config, 'algorithm') else 'skeleton'
        fillet_radius = config.fillet_radius if hasattr(config, 'fillet_radius') else 12.0
        
        # Generate roads
        roads = generate_road_network(
            site_boundary=site,
            algorithm=algorithm,
            fillet_radius=fillet_radius
        )
        
        # Convert to GeoJSON
        features = [
            linestring_to_geojson_feature(
                road,
                {"type": "road", "index": i}
            )
            for i, road in enumerate(roads)
        ]
        
        duration = (time.time() - start_time) * 1000
        
        return RoadGenerationResponse(
            success=True,
            roads=GeoJSONFeatureCollection(features=features),
            metadata={
                "algorithm": algorithm,
                "road_count": len(roads),
                "total_length": sum(r.length for r in roads),
                "fillet_radius": fillet_radius
            },
            duration_ms=duration
        )
        
    except Exception as e:
        logger.error(f"Road generation failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/subdivision", response_model=SubdivisionResponse)
async def generate_subdivision(request: SubdivisionRequest):
    """Subdivide site into lots using OBB Tree and Shape Grammar."""
    start_time = time.time()
    
    try:
        # Parse site boundary
        site = coords_to_polygon(request.site_boundary.coordinates)
        config = request.config or {}
        
        # Import generators
        from core.subdivision import subdivide_site
        
        # Get config values
        min_area = config.min_lot_area if hasattr(config, 'min_lot_area') else 1000.0
        max_area = config.max_lot_area if hasattr(config, 'max_lot_area') else 10000.0
        
        # Parse pre-computed roads if provided
        roads = None
        if request.roads:
            roads = [LineString(coords) for coords in request.roads]
        
        # Subdivide
        lots, green_spaces = subdivide_site(
            site_boundary=site,
            roads=roads,
            min_lot_area=min_area,
            max_lot_area=max_area
        )
        
        # Convert to GeoJSON
        lot_features = [
            polygon_to_geojson_feature(
                lot,
                {"type": "lot", "index": i, "area": lot.area}
            )
            for i, lot in enumerate(lots)
        ]
        
        green_features = [
            polygon_to_geojson_feature(
                green,
                {"type": "green_space", "index": i, "area": green.area}
            )
            for i, green in enumerate(green_spaces)
        ]
        
        duration = (time.time() - start_time) * 1000
        
        return SubdivisionResponse(
            success=True,
            lots=GeoJSONFeatureCollection(features=lot_features),
            green_spaces=GeoJSONFeatureCollection(features=green_features),
            metadata={
                "lot_count": len(lots),
                "green_count": len(green_spaces),
                "total_lot_area": sum(l.area for l in lots),
                "total_green_area": sum(g.area for g in green_spaces)
            },
            duration_ms=duration
        )
        
    except Exception as e:
        logger.error(f"Subdivision failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/full", response_model=FullPipelineResponse)
async def generate_full_plan(request: FullPipelineRequest):
    """Run complete procedural generation pipeline.
    
    Executes stages in order:
    1. roads: Generate road network
    2. subdivision: Divide into lots
    3. tiles: WFC tile placement (optional)
    4. postprocess: Add sidewalks, buffers
    """
    start_time = time.time()
    stages_results = []
    
    try:
        # Parse site boundary
        site = coords_to_polygon(request.site_boundary.coordinates)
        
        # Import pipeline
        from pipeline.procedural_pipeline import ProceduralPipeline, PipelineConfig
        
        # Build config from request
        pipeline_config = PipelineConfig()
        
        if request.road_config:
            pipeline_config.road_algorithm = request.road_config.algorithm
            pipeline_config.road_fillet_radius = request.road_config.fillet_radius
            
        if request.subdivision_config:
            pipeline_config.min_lot_area = request.subdivision_config.min_lot_area
            pipeline_config.max_lot_area = request.subdivision_config.max_lot_area
            pipeline_config.target_lot_width = request.subdivision_config.target_lot_width
            
        if request.postprocess_config:
            pipeline_config.sidewalk_width = request.postprocess_config.sidewalk_width
            pipeline_config.green_buffer_width = request.postprocess_config.green_buffer_width
        
        # Run pipeline
        pipeline = ProceduralPipeline(config=pipeline_config)
        result = pipeline.run_full(site)
        
        # Convert results to GeoJSON
        road_features = [
            linestring_to_geojson_feature(r, {"type": "road"})
            for r in result.roads
        ]
        
        lot_features = [
            polygon_to_geojson_feature(l, {"type": "lot", "area": l.area})
            for l in result.lots
        ]
        
        sidewalk_features = [
            polygon_to_geojson_feature(s, {"type": "sidewalk"})
            for s in result.sidewalks
        ]
        
        green_features = [
            polygon_to_geojson_feature(g, {"type": "green_space"})
            for g in result.green_spaces
        ]
        
        duration = (time.time() - start_time) * 1000
        
        return FullPipelineResponse(
            success=True,
            stages=[],  # TODO: Add per-stage results
            roads=GeoJSONFeatureCollection(features=road_features),
            lots=GeoJSONFeatureCollection(features=lot_features),
            sidewalks=GeoJSONFeatureCollection(features=sidewalk_features),
            green_spaces=GeoJSONFeatureCollection(features=green_features),
            metadata=result.metadata,
            total_duration_ms=duration
        )
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
