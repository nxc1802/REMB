"""DXF file handling utilities for importing and exporting geometry."""

import ezdxf
from shapely.geometry import Polygon, mapping
from shapely.ops import unary_union
from typing import Optional, List, Tuple
import io


def load_boundary_from_dxf(dxf_content: bytes) -> Optional[Polygon]:
    """
    Load site boundary from DXF file content.
    
    Args:
        dxf_content: Bytes content of DXF file
        
    Returns:
        Shapely Polygon or None if no valid boundary found
    """
    try:
        # Load DXF from bytes
        dxf_stream = io.BytesIO(dxf_content)
        doc = ezdxf.readfile(dxf_stream)
        msp = doc.modelspace()
        
        polygons = []
        
        # Extract LWPOLYLINE and POLYLINE entities
        for entity in msp.query('LWPOLYLINE, POLYLINE'):
            if entity.is_closed:
                points = list(entity.get_points())
                if len(points) >= 3:
                    coords = [(p[0], p[1]) for p in points]
                    # Close the polygon
                    if coords[0] != coords[-1]:
                        coords.append(coords[0])
                    try:
                        poly = Polygon(coords)
                        if poly.is_valid:
                            polygons.append(poly)
                    except:
                        continue
        
        # Also try to extract from LINE entities forming closed loops
        lines = list(msp.query('LINE'))
        if lines and not polygons:
            # Try to connect lines into closed loops
            # This is a simplified approach - could be improved
            for line in lines:
                start = (line.dxf.start.x, line.dxf.start.y)
                end = (line.dxf.end.x, line.dxf.end.y)
                # Simple heuristic: if it looks like a rectangle
                # You might need more sophisticated logic here
        
        if polygons:
            # Union all polygons and take the largest one
            if len(polygons) > 1:
                union = unary_union(polygons)
                if union.geom_type == 'Polygon':
                    return union
                elif union.geom_type == 'MultiPolygon':
                    # Return the largest polygon
                    return max(union.geoms, key=lambda p: p.area)
            return polygons[0]
        
        return None
        
    except Exception as e:
        print(f"Error loading DXF: {e}")
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
        doc.layers.add('BLOCKS', color=5)  # Blue for blocks
        doc.layers.add('LOTS', color=3)    # Green for lots
        doc.layers.add('PARKS', color=2)   # Yellow for parks
        doc.layers.add('BOUNDARY', color=7) # White for boundary
        
        # Add geometries
        for item in geometries:
            geom = item.get('geometry')
            props = item.get('properties', {})
            geom_type = props.get('type', 'lot')
            
            # Determine layer
            if geom_type == 'block':
                layer = 'BLOCKS'
            elif geom_type == 'park':
                layer = 'PARKS'
            else:
                layer = 'LOTS'
            
            # Get coordinates
            if geom and 'coordinates' in geom:
                coords = geom['coordinates']
                if coords and len(coords) > 0:
                    points = coords[0]  # Exterior ring
                    
                    # Add as LWPOLYLINE
                    if len(points) >= 3:
                        # Convert to 2D points (x, y)
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
        print(f"Error exporting DXF: {e}")
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
        dxf_stream = io.BytesIO(dxf_content)
        doc = ezdxf.readfile(dxf_stream)
        msp = doc.modelspace()
        
        # Count entities
        polylines = len(list(msp.query('LWPOLYLINE, POLYLINE')))
        lines = len(list(msp.query('LINE')))
        
        if polylines == 0 and lines == 0:
            return False, "No polylines or lines found in DXF"
        
        return True, f"Valid DXF: {polylines} polylines, {lines} lines"
        
    except Exception as e:
        return False, f"Invalid DXF: {str(e)}"
