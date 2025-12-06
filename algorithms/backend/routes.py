"""API routes for land redistribution algorithm."""

from fastapi import APIRouter, HTTPException
from typing import List
import traceback
from shapely.geometry import Polygon, mapping

from models import (
    OptimizationRequest,
    OptimizationResponse,
    StageResult
)
from algorithm import LandRedistributionPipeline

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
            stage2_features.append({
                "type": "Feature",
                "geometry": polygon_to_geojson(lot['geometry']),
                "properties": {
                    "stage": "subdivision",
                    "type": "lot",
                    "width": lot['width']
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
        
        stage2_geoms = {
            "type": "FeatureCollection",
            "features": stage2_features
        }
        
        stages.append(StageResult(
            stage_name="Block Subdivision (OR-Tools)",
            geometry=stage2_geoms,
            metrics=result['stage2']['metrics'],
            parameters={
                "min_lot_width": config['min_lot_width'],
                "max_lot_width": config['max_lot_width'],
                "target_lot_width": config['target_lot_width']
            }
        ))
        
        # Build response
        return OptimizationResponse(
            success=True,
            message="Optimization completed successfully",
            stages=stages,
            final_layout=stage2_geoms,
            total_lots=result['total_lots'],
            statistics={
                "total_blocks": result['stage1']['metrics']['total_blocks'],
                "total_lots": result['stage2']['metrics']['total_lots'],
                "total_parks": result['stage2']['metrics']['total_parks'],
                "optimal_spacing": result['stage1']['spacing'],
                "optimal_angle": result['stage1']['angle'],
                "avg_lot_width": result['stage2']['metrics']['avg_lot_width']
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
