"""Post-processing module for aesthetic enhancement.

Contains algorithms for:
- Buffer zone generation (sidewalks, green buffers)
- Corner treatment (fillet, chamfer)
- Detail generation
"""

from typing import List
from shapely.geometry import Polygon, LineString


def generate_sidewalks(
    roads: List[LineString],
    width: float = 2.0
) -> List[Polygon]:
    """Generate sidewalk polygons along roads.
    
    Args:
        roads: Road centerlines
        width: Sidewalk width (m)
        
    Returns:
        Sidewalk polygons
    """
    sidewalks = []
    
    for road in roads:
        try:
            # Buffer road for full width
            road_buffer = road.buffer(6)  # 12m road
            sidewalk_outer = road.buffer(6 + width)
            
            # Sidewalk is the ring
            sidewalk = sidewalk_outer.difference(road_buffer)
            
            if not sidewalk.is_empty:
                if sidewalk.geom_type == 'Polygon':
                    sidewalks.append(sidewalk)
                elif sidewalk.geom_type == 'MultiPolygon':
                    sidewalks.extend(list(sidewalk.geoms))
        except Exception:
            pass
            
    return sidewalks


def generate_green_buffer(
    lot: Polygon,
    buffer_width: float = 5.0
) -> Polygon:
    """Create green buffer ring around lot.
    
    Args:
        lot: Lot polygon
        buffer_width: Buffer width (m)
        
    Returns:
        Green buffer polygon
    """
    inner = lot.buffer(-buffer_width)
    
    if inner.is_empty:
        return Polygon()
        
    buffer_zone = lot.difference(inner)
    
    if buffer_zone.geom_type == 'MultiPolygon':
        return max(buffer_zone.geoms, key=lambda g: g.area)
        
    return buffer_zone


__all__ = ["generate_sidewalks", "generate_green_buffer"]
