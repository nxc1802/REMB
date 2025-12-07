"""API routes for land redistribution algorithm."""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response
from typing import List
import traceback
from shapely.geometry import Polygon, mapping, LineString, Point

from models import (
    OptimizationRequest,
    OptimizationResponse,
    StageResult
)
from algorithm import LandRedistributionPipeline
from dxf_utils import load_boundary_from_dxf, export_to_dxf, validate_dxf

router = APIRouter()


def land_plot_to_polygon(land_plot: dict) -> Polygon:
    """Convert LandPlot model to Shapely Polygon."""
    coords = land_plot['coordinates'][0]  # Exterior ring
    return Polygon(coords)


def polygon_to_geojson(poly: Polygon) -> dict:
    """Convert Shapely Polygon to GeoJSON."""
    return mapping(poly)


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_full(request: OptimizationRequest):
    """
    Run complete land redistribution optimization pipeline.
    
    This endpoint executes all stages:
    1. Grid optimization (NSGA-II)
    2. Block subdivision (OR-Tools)
    3. Infrastructure planning
    
    Returns detailed results with process visualization data.
    """
    try:
        # Convert input land plots to Shapely polygons
        land_polygons = [land_plot_to_polygon(plot.dict()) for plot in request.land_plots]
        
        # Create pipeline
        config = request.config.dict()
        pipeline = LandRedistributionPipeline(land_polygons, config)
        
        # Run optimization
        result = pipeline.run_full_pipeline()
        
        # Build stage results
        stages = []
        
        # Stage 1: Grid Optimization
        stage1_geoms = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": polygon_to_geojson(block),
                    "properties": {"stage": "grid", "type": "block"}
                }
                for block in result['stage1']['blocks']
            ]
        }
        
        stages.append(StageResult(
            stage_name="Grid Optimization (NSGA-II)",
            geometry=stage1_geoms,
            metrics=result['stage1']['metrics'],
            parameters={
                "spacing": result['stage1']['spacing'],
                "angle": result['stage1']['angle']
            }
        ))
        
        # Stage 2: Subdivision
        stage2_features = []
        
        # Add lots
        for lot in result['stage2']['lots']:
            lot_props = {
                "stage": "subdivision",
                "type": "lot",
                "width": lot['width']
            }
            stage2_features.append({
                "type": "Feature",
                "geometry": polygon_to_geojson(lot['geometry']),
                "properties": lot_props
            })
            
            # Setback (Network visualization will need this as separate line usually, 
            # or frontend can render it if passed as property geometry)
            if lot.get('buildable'):
                stage2_features.append({
                    "type": "Feature",
                    "geometry": polygon_to_geojson(lot['buildable']),
                    "properties": {
                        "stage": "subdivision",
                        "type": "setback",
                        "parent_lot": str(lot['geometry'])
                    }
                })
        
        # Add parks
        for park in result['stage2']['parks']:
            stage2_features.append({
                "type": "Feature",
                "geometry": polygon_to_geojson(park),
                "properties": {
                    "stage": "subdivision",
                    "type": "park"
                }
            })
        
        
        # Add Service Blocks
        for block in result['classification'].get('service', []):
            stage2_features.append({
                "type": "Feature",
                "geometry": polygon_to_geojson(block),
                "properties": {
                    "stage": "subdivision",
                    "type": "service",
                    "label": "Operating Center/Parking"
                }
            })

        # Add XLNT Block
        for block in result['classification'].get('xlnt', []):
            stage2_features.append({
                "type": "Feature",
                "geometry": polygon_to_geojson(block),
                "properties": {
                    "stage": "subdivision",
                    "type": "xlnt",
                    "label": "Wastewater Treatment"
                }
            })

        stage2_geoms = {
            "type": "FeatureCollection",
            "features": stage2_features
        }
        
        stages.append(StageResult(
            stage_name="Block Subdivision (OR-Tools)",
            geometry=stage2_geoms,
            metrics={
                **result['stage2']['metrics'],
                "service_count": result['classification']['service_count'],
                "xlnt_count": result['classification']['xlnt_count']
            },
            parameters={
                "min_lot_width": config['min_lot_width'],
                "max_lot_width": config['max_lot_width'],
                "target_lot_width": config['target_lot_width']
            }
        ))
        
        # Stage 3: Infrastructure
        stage3_features = []
        
        # Add road network
        if 'road_network' in result['stage3']:
            road_feat = {
                "type": "Feature",
                "geometry": result['stage3']['road_network'],
                "properties": {
                    "stage": "infrastructure",
                    "type": "road_network",
                    "label": "Transportation Infra"
                }
            }
            # PREPEND roads so they are at bottom layer
            stage3_features.insert(0, road_feat)

        # Add connection lines
        for conn_coords in result['stage3']['connections']:
            stage3_features.append({
                "type": "Feature",
                "geometry": mapping(LineString(conn_coords)),
                "properties": {
                    "stage": "infrastructure",
                    "type": "connection",
                    "layer": "electricity_water"
                }
            })
            
        # Add Transformers
        if 'transformers' in result['stage3']:
            for tf_coords in result['stage3']['transformers']:
                stage3_features.append({
                    "type": "Feature",
                    "geometry": mapping(Point(tf_coords)),
                    "properties": {
                        "stage": "infrastructure",
                        "type": "transformer",
                        "label": "Transformer Station"
                    }
                })

        # Add drainage
        for drainage in result['stage3']['drainage']:
            # Create a line for the arrow
            start = drainage['start']
            vec = drainage['vector']
            end = (start[0] + vec[0], start[1] + vec[1])
            stage3_features.append({
                "type": "Feature",
                "geometry": mapping(LineString([start, end])),
                "properties": {
                    "stage": "infrastructure",
                    "type": "drainage"
                }
            })
            
        stage3_geoms = {
            "type": "FeatureCollection",
            "features": stage3_features + stage2_features # Include base map
        }
        
        stages.append(StageResult(
            stage_name="Infrastructure (MST & Drainage & Roads)",
            geometry=stage3_geoms,
            metrics={
                "total_connections": len(result['stage3']['connections']),
                "drainage_points": len(result['stage3']['drainage']),
                "transformers": len(result.get('stage3', {}).get('transformers', []))
            },
            parameters={}
        ))
        
        # Build response
        return OptimizationResponse(
            success=True,
            message="Optimization completed successfully",
            stages=stages,
            final_layout=stage3_geoms,
            total_lots=result['total_lots'],
            statistics={
                "total_blocks": result['stage1']['metrics']['total_blocks'],
                "total_lots": result['stage2']['metrics']['total_lots'],
                "total_parks": result['stage2']['metrics']['total_parks'],
                "optimal_spacing": result['stage1']['spacing'],
                "optimal_angle": result['stage1']['angle'],
                "avg_lot_width": result['stage2']['metrics']['avg_lot_width'],
                "service_area_count": result['classification']['service_count'] + result['classification']['xlnt_count']
            }
        )
        
    except Exception as e:
        error_msg = f"Optimization failed: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/stage1", response_model=OptimizationResponse)
async def optimize_stage1(request: OptimizationRequest):
    """Run only grid optimization stage."""
    try:
        land_polygons = [land_plot_to_polygon(plot.dict()) for plot in request.land_plots]
        
        config = request.config.dict()
        pipeline = LandRedistributionPipeline(land_polygons, config)
        
        result = pipeline.run_stage1()
        
        stage_geoms = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": polygon_to_geojson(block),
                    "properties": {"stage": "grid", "type": "block"}
                }
                for block in result['blocks']
            ]
        }
        
        return OptimizationResponse(
            success=True,
            message="Stage 1 (Grid Optimization) completed",
            stages=[StageResult(
                stage_name="Grid Optimization (NSGA-II)",
                geometry=stage_geoms,
                metrics=result['metrics'],
                parameters={
                    "spacing": result['spacing'],
                    "angle": result['angle']
                }
            )],
            statistics=result['metrics']
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stage 1 failed: {str(e)}")


@router.post("/upload-dxf")
async def upload_dxf(file: UploadFile = File(...)):
    """
    Upload and parse DXF file to extract boundary polygon.
    
    Returns GeoJSON polygon that can be used as input.
    """
    try:
        # Read file content
        content = await file.read()
        
        # Validate DXF
        is_valid, message = validate_dxf(content)
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
        
        # Load boundary
        polygon = load_boundary_from_dxf(content)
        
        if polygon is None:
            raise HTTPException(
                status_code=400, 
                detail="Could not extract boundary polygon from DXF. Make sure it contains closed polylines."
            )
        
        # Convert to GeoJSON
        geojson = {
            "type": "Polygon",
            "coordinates": [list(polygon.exterior.coords)],
            "properties": {
                "source": "dxf",
                "filename": file.filename,
                "area": polygon.area
            }
        }
        
        return {
            "success": True,
            "message": f"Successfully extracted boundary from {file.filename}",
            "polygon": geojson,
            "area": polygon.area,
            "bounds": polygon.bounds
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process DXF: {str(e)}")


@router.post("/export-dxf")
async def export_dxf_endpoint(request: dict):
    """
    Export optimization results to DXF format.
    
    Expects: {"result": OptimizationResponse}
    Returns: DXF file
    """
    try:
        result = request.get('result')
        if not result:
            raise HTTPException(status_code=400, detail="No result data provided")
        
        # Get final layout or last stage
        geometries = []
        
        if 'final_layout' in result and result['final_layout']:
            features = result['final_layout'].get('features', [])
            geometries = features
        elif 'stages' in result and len(result['stages']) > 0:
            last_stage = result['stages'][-1]
            features = last_stage.get('geometry', {}).get('features', [])
            geometries = features
        
        if not geometries:
            raise HTTPException(status_code=400, detail="No geometries to export")
        
        # Export to DXF
        dxf_bytes = export_to_dxf(geometries)
        
        if not dxf_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate DXF")
        
        # Return as downloadable file
        return Response(
            content=dxf_bytes,
            media_type="application/dxf",
            headers={
                "Content-Disposition": "attachment; filename=land_redistribution.dxf"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
