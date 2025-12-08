"""DXF file handling utilities for importing and exporting geometry.

Based on REMB_Production_Final_Reliable.ipynb converter logic.
"""

import logging
import ezdxf
from shapely.geometry import Polygon, mapping, LineString
from shapely.ops import unary_union, polygonize
from typing import Optional, List, Tuple
import io

logger = logging.getLogger(__name__)


def load_boundary_from_dxf(dxf_content: bytes) -> Optional[Polygon]:
    """
    Load site boundary from DXF file content.
    
    Uses the same logic as notebook's load_boundary_from_dxf function:
    - Looks for closed LWPOLYLINE entities
    - Returns the largest valid polygon found
    
    Args:
        dxf_content: Bytes content of DXF file
        
    Returns:
        Shapely Polygon or None if no valid boundary found
    """
    try:
        # Load DXF from bytes
        # For maximum compatibility, especially with old DXF formats (R11/R12),
        # use tempfile approach as it preserves all entity data
        import tempfile
        import os
        
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
            
            # Fallback: Try stream methods
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
        
        # Extract LWPOLYLINE entities (matching notebook logic)
        for entity in msp:
            if entity.dxftype() == 'LWPOLYLINE' and entity.is_closed:
                try:
                    # Get points in xy format (matching notebook)
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
        
        # Try to build polygons from LINE entities (for CAD files with separate lines)
        if not largest:
            try:
                from shapely.ops import polygonize, unary_union
                from shapely.geometry import MultiLineString
                
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
            # Scale coordinates by 1.5x for better visualization
            from shapely import affinity
            largest = affinity.scale(largest, xfact=1.5, yfact=1.5, origin='centroid')
            logger.info(f"Boundary loaded and scaled 1.5x: {largest.area/10000:.2f} ha")
            return largest
        
        logger.warning("No valid closed polylines found in DXF")
        return None
        
    except Exception as e:
        logger.error(f"Error loading DXF: {e}")
        return None


def export_to_dxf(geometries: List[dict], output_type: str = 'final') -> bytes:
    """
    Export geometries to DXF format.
    
    Args:
        geometries: List of geometry dicts with 'geometry' and 'properties'
        output_type: Type of output ('stage1', 'stage2', 'final')
        
    Returns:
        DXF file content as bytes
    """
    try:
        # Create new DXF document
        doc = ezdxf.new('R2010')
        msp = doc.modelspace()
        
        # Create layers
        doc.layers.add('BLOCKS', color=5)      # Blue for blocks
        doc.layers.add('LOTS', color=3)        # Green for lots
        doc.layers.add('PARKS', color=2)       # Yellow for parks
        doc.layers.add('SERVICE', color=4)     # Cyan for service
        doc.layers.add('ROADS', color=8)       # Gray for roads
        doc.layers.add('INFRASTRUCTURE', color=1)  # Red for infrastructure
        
        # Add geometries
        for item in geometries:
            geom = item.get('geometry')
            props = item.get('properties', {})
            geom_type = props.get('type', 'lot')
            
            # Determine layer
            layer_map = {
                'block': 'BLOCKS',
                'park': 'PARKS',
                'service': 'SERVICE',
                'xlnt': 'SERVICE',
                'road_network': 'ROADS',
                'connection': 'INFRASTRUCTURE',
                'transformer': 'INFRASTRUCTURE',
                'drainage': 'INFRASTRUCTURE',
                'lot': 'LOTS',
                'setback': 'LOTS'
            }
            layer = layer_map.get(geom_type, 'LOTS')
            
            # Get coordinates
            if geom and 'coordinates' in geom:
                coords = geom['coordinates']
                geom_geom_type = geom.get('type', 'Polygon')
                
                # Handle different geometry types
                if geom_geom_type == 'Point':
                    # Point: [x, y]
                    if isinstance(coords, list) and len(coords) >= 2:
                        msp.add_circle(
                            center=(coords[0], coords[1]),
                            radius=2.0,
                            dxfattribs={'layer': layer}
                        )
                        
                elif geom_geom_type == 'LineString':
                    # LineString: [[x1, y1], [x2, y2], ...]
                    if isinstance(coords, list) and len(coords) > 0:
                        if all(isinstance(p, (list, tuple)) and len(p) >= 2 for p in coords):
                            points_2d = [(p[0], p[1]) for p in coords]
                            if len(points_2d) >= 2:
                                msp.add_lwpolyline(
                                    points_2d,
                                    dxfattribs={'layer': layer, 'closed': False}
                                )
                                
                elif geom_geom_type == 'Polygon':
                    # Polygon: [[[x1, y1], [x2, y2], ...]]  (exterior ring)
                    if isinstance(coords, list) and len(coords) > 0:
                        points = coords[0] if isinstance(coords[0], list) else coords
                        
                        # Validate points structure
                        if isinstance(points, list) and len(points) >= 3:
                            if all(isinstance(p, (list, tuple)) and len(p) >= 2 for p in points):
                                points_2d = [(p[0], p[1]) for p in points]
                                
                                # Create closed polyline
                                msp.add_lwpolyline(
                                    points_2d,
                                    dxfattribs={
                                        'layer': layer,
                                        'closed': True
                                    }
                                )
        
        # Save to bytes
        stream = io.StringIO()
        doc.write(stream, fmt='asc')  # ASCII format for better compatibility
        return stream.getvalue().encode('utf-8')
        
    except Exception as e:
        logger.error(f"Error exporting DXF: {e}")
        return b''


def validate_dxf(dxf_content: bytes) -> Tuple[bool, str]:
    """
    Validate DXF file and return status.
    
    Args:
        dxf_content: DXF file bytes
        
    Returns:
        (is_valid, message)
    """
    try:
        # Load DXF for validation
        # Use tempfile method for maximum compatibility
        import tempfile
        import os
        
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
