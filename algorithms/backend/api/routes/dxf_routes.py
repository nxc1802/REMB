"""DXF file handling routes."""

import logging
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response

from utils.dxf_utils import load_boundary_from_dxf, export_to_dxf, validate_dxf

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload-dxf")
async def upload_dxf(file: UploadFile = File(...)):
    """
    Upload and parse DXF file to extract boundary polygon.
    
    Returns GeoJSON polygon that can be used as input.
    """
    try:
        content = await file.read()
        
        is_valid, message = validate_dxf(content)
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
        
        polygon = load_boundary_from_dxf(content)
        
        if polygon is None:
            raise HTTPException(
                status_code=400, 
                detail="Could not extract boundary polygon from DXF. Make sure it contains closed polylines."
            )
        
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
        logger.error(f"DXF processing failed: {e}")
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
        
        dxf_bytes = export_to_dxf(geometries)
        
        if not dxf_bytes:
            raise HTTPException(status_code=500, detail="Failed to generate DXF")
        
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
        logger.error(f"DXF export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
