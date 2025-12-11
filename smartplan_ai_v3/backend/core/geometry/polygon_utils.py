"""Polygon utility functions using Shapely."""

from typing import List, Tuple, Optional
from shapely.geometry import Polygon, Point, mapping, shape
from shapely.affinity import scale, rotate, translate
import numpy as np


def polygon_to_coords(polygon: Polygon) -> List[List[float]]:
    """Convert Shapely Polygon to coordinate list.
    
    Args:
        polygon: Shapely Polygon object
        
    Returns:
        List of [x, y] coordinates
    """
    if polygon is None or polygon.is_empty:
        return []
    
    coords = list(polygon.exterior.coords)
    # Remove the closing coordinate (same as first)
    if coords and coords[0] == coords[-1]:
        coords = coords[:-1]
    
    return [[float(x), float(y)] for x, y in coords]


def coords_to_polygon(coords: List[List[float]]) -> Optional[Polygon]:
    """Convert coordinate list to Shapely Polygon.
    
    Args:
        coords: List of [x, y] coordinates
        
    Returns:
        Shapely Polygon or None if invalid
    """
    if not coords or len(coords) < 3:
        return None
    
    try:
        # Ensure polygon is closed
        if coords[0] != coords[-1]:
            coords = coords + [coords[0]]
        
        polygon = Polygon(coords)
        
        if not polygon.is_valid:
            # Try to fix invalid polygon
            polygon = polygon.buffer(0)
        
        return polygon if polygon.is_valid and not polygon.is_empty else None
    except Exception:
        return None


def calculate_centroid(polygon: Polygon) -> Tuple[float, float]:
    """Get centroid coordinates of polygon.
    
    Args:
        polygon: Shapely Polygon object
        
    Returns:
        Tuple of (x, y) centroid coordinates
    """
    if polygon is None or polygon.is_empty:
        return (0.0, 0.0)
    
    centroid = polygon.centroid
    return (float(centroid.x), float(centroid.y))


def buffer_polygon(polygon: Polygon, distance: float) -> Optional[Polygon]:
    """Add buffer (margin) around polygon.
    
    Positive distance expands, negative shrinks.
    
    Args:
        polygon: Shapely Polygon object
        distance: Buffer distance in meters
        
    Returns:
        Buffered polygon or None if result is invalid
    """
    if polygon is None or polygon.is_empty:
        return None
    
    try:
        buffered = polygon.buffer(distance)
        
        # Buffer might return MultiPolygon for negative values
        if buffered.geom_type == 'MultiPolygon':
            # Get the largest polygon
            buffered = max(buffered.geoms, key=lambda p: p.area)
        
        return buffered if not buffered.is_empty else None
    except Exception:
        return None


def polygon_to_geojson(polygon: Polygon, properties: dict = None) -> dict:
    """Convert Shapely Polygon to GeoJSON Feature.
    
    Args:
        polygon: Shapely Polygon object
        properties: Optional properties dict
        
    Returns:
        GeoJSON Feature dict
    """
    return {
        "type": "Feature",
        "geometry": mapping(polygon),
        "properties": properties or {}
    }


def geojson_to_polygon(geojson: dict) -> Optional[Polygon]:
    """Convert GeoJSON to Shapely Polygon.
    
    Args:
        geojson: GeoJSON Feature or Geometry dict
        
    Returns:
        Shapely Polygon or None
    """
    try:
        # Handle Feature vs Geometry
        geometry = geojson.get("geometry", geojson)
        return shape(geometry)
    except Exception:
        return None


def calculate_oriented_bounding_box(polygon: Polygon) -> Tuple[Polygon, float]:
    """Calculate the minimum oriented bounding box of a polygon.
    
    Args:
        polygon: Shapely Polygon object
        
    Returns:
        Tuple of (OBB polygon, rotation angle in degrees)
    """
    if polygon is None or polygon.is_empty:
        return None, 0.0
    
    # Get minimum rotated rectangle
    obb = polygon.minimum_rotated_rectangle
    
    # Calculate rotation angle
    coords = list(obb.exterior.coords)
    edge1 = np.array(coords[1]) - np.array(coords[0])
    angle = np.degrees(np.arctan2(edge1[1], edge1[0]))
    
    return obb, angle


def get_polygon_dimensions(polygon: Polygon) -> Tuple[float, float]:
    """Get width and height of polygon's bounding box.
    
    Args:
        polygon: Shapely Polygon object
        
    Returns:
        Tuple of (width, height) in meters
    """
    if polygon is None or polygon.is_empty:
        return (0.0, 0.0)
    
    bounds = polygon.bounds  # (minx, miny, maxx, maxy)
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    
    return (width, height)
