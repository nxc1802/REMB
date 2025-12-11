"""DXF import/export routes."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from shapely.geometry import Polygon, mapping

from api.schemas.response_schemas import GeoJSONFeature, GeoJSONFeatureCollection

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload-dxf")
async def upload_dxf(file: UploadFile = File(...)):
    """Upload DXF file and extract site boundary.
    
    Reads DXF file and extracts closed polylines as potential site boundaries.
    """
    try:
        # Read file content
        content = await file.read()
        
        # Import DXF utils
        from utils.dxf_utils import parse_dxf_boundary
        
        # Parse DXF
        polygons = parse_dxf_boundary(content, file.filename)
        
        if not polygons:
            raise HTTPException(
                status_code=400,
                detail="No closed polylines found in DXF file"
            )
        
        # Convert to GeoJSON
        features = [
            GeoJSONFeature(
                type="Feature",
                geometry=mapping(poly),
                properties={
                    "type": "boundary",
                    "index": i,
                    "area": poly.area
                }
            )
            for i, poly in enumerate(polygons)
        ]
        
        return {
            "success": True,
            "filename": file.filename,
            "boundaries": GeoJSONFeatureCollection(features=features),
            "count": len(polygons)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DXF upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export-dxf")
async def export_dxf(
    lots: Optional[list] = None,
    roads: Optional[list] = None,
    filename: str = "output.dxf"
):
    """Export generated layout to DXF file."""
    try:
        from utils.dxf_utils import export_to_dxf
        from fastapi.responses import StreamingResponse
        import io
        
        # Create DXF
        dxf_content = export_to_dxf(lots=lots, roads=roads)
        
        # Return as downloadable file
        buffer = io.BytesIO(dxf_content)
        
        return StreamingResponse(
            buffer,
            media_type="application/dxf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"DXF export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
