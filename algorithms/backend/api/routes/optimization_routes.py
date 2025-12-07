"""Optimization API routes."""

import logging
import traceback
from fastapi import APIRouter, HTTPException
from shapely.geometry import Polygon, mapping, LineString, Point

from api.schemas.request_schemas import OptimizationRequest
from api.schemas.response_schemas import OptimizationResponse, StageResult
from pipeline.land_redistribution import LandRedistributionPipeline

logger = logging.getLogger(__name__)
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
            
            # Setback
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
            "features": stage3_features + stage2_features
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
        logger.error(error_msg)
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
        logger.error(f"Stage 1 failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stage 1 failed: {str(e)}")
