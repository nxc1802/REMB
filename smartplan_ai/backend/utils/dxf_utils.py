"""DXF file handling utilities.

Based on algorithms/backend/utils/dxf_utils.py with robust parsing.
"""

import io
import logging
import tempfile
import os
from typing import List, Optional, Tuple, Union

import ezdxf
from shapely.geometry import Polygon, LineString
from shapely.ops import polygonize

logger = logging.getLogger(__name__)


def load_boundary_from_dxf(dxf_content: bytes) -> Optional[Polygon]:
    """
    Load site boundary from DXF file content.
    
    Uses robust parsing with multiple fallback methods:
    - Tempfile method for maximum compatibility
    - Multiple encoding attempts
    - Support for LWPOLYLINE, POLYLINE, and LINE entities
    
    Args:
        dxf_content: Bytes content of DXF file
        
    Returns:
        Shapely Polygon or None if no valid boundary found
    """
    try:
        doc = None
        tmp_path = None
        
        try:
            # Write bytes to temporary file
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.dxf', delete=False) as tmp:
                tmp.write(dxf_content)
                tmp_path = tmp.name
            
            # Read using ezdxf.readfile (most reliable method)
            doc = ezdxf.readfile(tmp_path)
            logger.info("Successfully loaded DXF using tempfile method")
            
        except Exception as e:
            logger.warning(f"Tempfile method failed: {e}, trying stream methods")
            
            # Fallback: Try stream methods with multiple encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'utf-16']
            
            for encoding in encodings:
                try:
                    text_content = dxf_content.decode(encoding)
                    text_stream = io.StringIO(text_content)
                    doc = ezdxf.read(text_stream)
                    logger.info(f"Successfully loaded DXF with {encoding} encoding")
                    break
                except (UnicodeDecodeError, AttributeError):
                    continue
                except Exception:
                    continue
            
            # Last resort: Binary stream
            if doc is None:
                try:
                    dxf_stream = io.BytesIO(dxf_content)
                    doc = ezdxf.read(dxf_stream)
                    logger.info("Successfully loaded DXF in binary format")
                except Exception as final_error:
                    logger.error(f"Failed to load DXF in any format: {final_error}")
                    return None
        finally:
            # Clean up temp file
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except:
                    pass
        
        if doc is None:
            return None
        
        msp = doc.modelspace()
        
        largest = None
        max_area = 0.0
        
        # Extract LWPOLYLINE entities
        for entity in msp:
            if entity.dxftype() == 'LWPOLYLINE' and entity.is_closed:
                try:
                    pts = list(entity.get_points(format='xy'))
                    
                    if len(pts) >= 3:
                        poly = Polygon(pts)
                        
                        if poly.is_valid and poly.area > max_area:
                            max_area = poly.area
                            largest = poly
                            
                except Exception as e:
                    logger.warning(f"Failed to process LWPOLYLINE: {e}")
                    continue
        
        # Also try POLYLINE entities as fallback
        if not largest:
            for entity in msp.query('POLYLINE'):
                if entity.is_closed:
                    try:
                        points = list(entity.get_points())
                        if len(points) >= 3:
                            coords = [(p[0], p[1]) for p in points]
                            poly = Polygon(coords)
                            
                            if poly.is_valid and poly.area > max_area:
                                max_area = poly.area
                                largest = poly
                                
                    except Exception as e:
                        logger.warning(f"Failed to process POLYLINE: {e}")
                        continue
        
        # Try to build polygons from LINE entities
        if not largest:
            try:
                lines = list(msp.query('LINE'))
                if lines:
                    logger.info(f"Attempting to build polygon from {len(lines)} LINE entities")
                    
                    # Convert LINE entities to shapely LineStrings
                    line_segments = []
                    for line in lines:
                        start = (line.dxf.start.x, line.dxf.start.y)
                        end = (line.dxf.end.x, line.dxf.end.y)
                        line_segments.append(LineString([start, end]))
                    
                    # Use polygonize to find closed polygons from line network
                    polygons = list(polygonize(line_segments))
                    
                    if polygons:
                        logger.info(f"Found {len(polygons)} polygons from LINE entities")
                        
                        # Find the largest valid polygon
                        for poly in polygons:
                            if poly.is_valid and poly.area > max_area:
                                max_area = poly.area
                                largest = poly
                    else:
                        logger.warning("Could not create polygons from LINE entities")
                        
            except Exception as e:
                logger.warning(f"Failed to process LINE entities: {e}")
        
        if largest:
            logger.info(f"Boundary loaded: {largest.area:.2f} m²")
            return largest
        
        logger.warning("No valid closed polylines found in DXF")
        return None
        
    except Exception as e:
        logger.error(f"Error loading DXF: {e}")
        return None


def parse_dxf_boundary(
    content: Union[bytes, str],
    filename: str = "input.dxf"
) -> List[Polygon]:
    """Parse DXF file content and extract polygons.
    
    Args:
        content: DXF file content (bytes or string)
        filename: Original filename for logging
        
    Returns:
        List of Polygon objects extracted
    """
    # Convert string to bytes if needed
    if isinstance(content, str):
        content = content.encode('utf-8')
    
    # Use robust loader
    polygon = load_boundary_from_dxf(content)
    
    if polygon:
        return [polygon]
    
    return []


def export_to_dxf(
    lots: Optional[List[dict]] = None,
    roads: Optional[List[dict]] = None,
    green_spaces: Optional[List[dict]] = None
) -> bytes:
    """Export geometry to DXF format.
    
    Args:
        lots: List of lot GeoJSON features
        roads: List of road GeoJSON features
        green_spaces: List of green space GeoJSON features
        
    Returns:
        DXF file content as bytes
    """
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()
    
    # Create layers
    doc.layers.add('LOTS', color=3)        # Green
    doc.layers.add('ROADS', color=1)       # Red
    doc.layers.add('GREEN_SPACES', color=4)  # Cyan
    
    # Add lot polygons
    if lots:
        for lot in lots:
            coords = lot.get('geometry', {}).get('coordinates', [[]])
            if coords and coords[0]:
                points = [(x, y) for x, y in coords[0]]
                if len(points) >= 3:
                    msp.add_lwpolyline(points, close=True, dxfattribs={'layer': 'LOTS'})
                
    # Add road lines
    if roads:
        for road in roads:
            coords = road.get('geometry', {}).get('coordinates', [])
            if coords and len(coords) >= 2:
                points = [(x, y) for x, y in coords]
                msp.add_lwpolyline(points, dxfattribs={'layer': 'ROADS'})
                
    # Add green spaces
    if green_spaces:
        for green in green_spaces:
            coords = green.get('geometry', {}).get('coordinates', [[]])
            if coords and coords[0]:
                points = [(x, y) for x, y in coords[0]]
                if len(points) >= 3:
                    msp.add_lwpolyline(points, close=True, dxfattribs={'layer': 'GREEN_SPACES'})
    
    # Write to bytes
    stream = io.StringIO()
    doc.write(stream, fmt='asc')  # ASCII format for better compatibility
    return stream.getvalue().encode('utf-8')


def validate_dxf(dxf_content: bytes) -> Tuple[bool, str]:
    """
    Validate DXF file and return status.
    
    Args:
        dxf_content: DXF file bytes
        
    Returns:
        (is_valid, message)
    """
    try:
        doc = None
        tmp_path = None
        
        try:
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.dxf', delete=False) as tmp:
                tmp.write(dxf_content)
                tmp_path = tmp.name
            
            doc = ezdxf.readfile(tmp_path)
            
        except Exception:
            # Fallback to stream methods
            encodings = ['utf-8', 'latin-1', 'cp1252', 'utf-16']
            
            for encoding in encodings:
                try:
                    text_content = dxf_content.decode(encoding)
                    text_stream = io.StringIO(text_content)
                    doc = ezdxf.read(text_stream)
                    break
                except (UnicodeDecodeError, AttributeError, Exception):
                    continue
            
            if doc is None:
                try:
                    dxf_stream = io.BytesIO(dxf_content)
                    doc = ezdxf.read(dxf_stream)
                except Exception as e:
                    return False, f"Failed to parse DXF: {str(e)}"
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                    
        msp = doc.modelspace()
        
        # Count entities
        lwpolylines = sum(1 for e in msp if e.dxftype() == 'LWPOLYLINE')
        polylines = len(list(msp.query('POLYLINE')))
        lines = len(list(msp.query('LINE')))
        
        total_entities = lwpolylines + polylines + lines
        
        if total_entities == 0:
            return False, "No polylines or lines found in DXF"
        
        # Check for closed polylines
        closed_count = sum(1 for e in msp if e.dxftype() == 'LWPOLYLINE' and e.is_closed)
        
        msg = f"Valid DXF: {lwpolylines} LWPOLYLINE ({closed_count} closed), {polylines} POLYLINE, {lines} LINE"
        return True, msg
        
    except Exception as e:
        return False, f"Invalid DXF: {str(e)}"
