"""
Polygon utility functions for geometry processing.

Provides helper functions for Shapely polygon operations,
elevation calculations, and geometry normalization.
"""

import logging
from typing import List, Union, Optional

from shapely.geometry import Polygon, MultiPolygon, GeometryCollection
from shapely.ops import unary_union

logger = logging.getLogger(__name__)


def get_elevation(x: float, y: float) -> float:
    """
    Simulate terrain elevation (sloping from NW to SE).
    
    This is a simple linear model: z = 50 - 0.02x - 0.03y
    Used for determining WWTP placement (lowest point).
    
    Args:
        x: X coordinate
        y: Y coordinate
        
    Returns:
        Simulated elevation value
    """
    return 50.0 - (x * 0.02) - (y * 0.03)


def normalize_geometry_list(
    geometry: Union[Polygon, MultiPolygon, GeometryCollection, None]
) -> List[Polygon]:
    """
    Convert various geometry types to a flat list of Polygons.
    
    Handles GeometryCollection, MultiPolygon, single Polygon, or None.
    
    Args:
        geometry: Input geometry of various types
        
    Returns:
        List of Polygon objects (may be empty)
    """
    if geometry is None or geometry.is_empty:
        return []
    
    if hasattr(geometry, 'geoms'):
        # GeometryCollection or MultiPolygon
        result = []
        for geom in geometry.geoms:
            if geom.geom_type == 'Polygon' and not geom.is_empty:
                result.append(geom)
        return result
    elif geometry.geom_type == 'Polygon':
        return [geometry]
    else:
        logger.warning(f"Unexpected geometry type: {geometry.geom_type}")
        return []


def merge_polygons(polygons: List[Polygon]) -> Polygon:
    """
    Merge multiple polygons into a single polygon using unary_union.
    
    Args:
        polygons: List of Polygon objects
        
    Returns:
        Merged polygon (may be MultiPolygon if non-contiguous)
    """
    if not polygons:
        return Polygon()
    
    if len(polygons) == 1:
        return polygons[0]
    
    return unary_union(polygons)


def filter_by_min_area(
    polygons: List[Polygon], 
    min_area: float
) -> List[Polygon]:
    """
    Filter polygons by minimum area threshold.
    
    Args:
        polygons: List of polygons to filter
        min_area: Minimum area threshold (m²)
        
    Returns:
        Filtered list of polygons meeting the area requirement
    """
    return [p for p in polygons if p.area >= min_area]


def sort_by_elevation(polygons: List[Polygon]) -> List[Polygon]:
    """
    Sort polygons by centroid elevation (lowest first).
    
    Useful for determining WWTP placement (should be at lowest point).
    
    Args:
        polygons: List of polygons to sort
        
    Returns:
        Sorted list (lowest elevation first)
    """
    return sorted(
        polygons, 
        key=lambda p: get_elevation(p.centroid.x, p.centroid.y)
    )


def calculate_block_quality_ratio(
    block: Polygon, 
    original_area: float
) -> float:
    """
    Calculate quality ratio of a block (actual area / original area).
    
    Used to classify blocks as residential, fragmented, or unusable.
    
    Args:
        block: Block polygon
        original_area: Original (full) block area before clipping
        
    Returns:
        Ratio between 0 and 1
    """
    if original_area <= 0:
        return 0.0
    return min(1.0, block.area / original_area)
