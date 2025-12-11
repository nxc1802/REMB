"""Utility routing for infrastructure (Electric/Water).

Final phase of the processing pipeline.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional
from shapely.geometry import Point, LineString, Polygon, mapping
import logging

from .graph_utils import (
    minimum_spanning_tree,
    points_to_linestrings,
    steiner_tree_approximation,
    connect_to_edge
)

logger = logging.getLogger(__name__)


@dataclass
class InfrastructureResult:
    """Result of infrastructure routing."""
    
    success: bool
    electric_lines: List[LineString] = field(default_factory=list)
    water_lines: List[LineString] = field(default_factory=list)
    total_electric_length: float = 0.0
    total_water_length: float = 0.0
    connection_points: List[Tuple[float, float]] = field(default_factory=list)
    error: str = None
    
    def to_geojson(self) -> dict:
        """Convert to GeoJSON FeatureCollection."""
        features = []
        
        for i, line in enumerate(self.electric_lines):
            features.append({
                "type": "Feature",
                "geometry": mapping(line),
                "properties": {
                    "type": "electric",
                    "id": f"E{i+1}",
                    "length": line.length
                }
            })
        
        for i, line in enumerate(self.water_lines):
            features.append({
                "type": "Feature",
                "geometry": mapping(line),
                "properties": {
                    "type": "water",
                    "id": f"W{i+1}",
                    "length": line.length
                }
            })
        
        return {
            "type": "FeatureCollection",
            "features": features
        }


def route_utilities(
    assets: List[Dict[str, Any]],
    connection_point: Tuple[float, float],
    boundary: Polygon = None,
    use_steiner: bool = False
) -> InfrastructureResult:
    """Route electric and water utilities to all assets.
    
    Uses MST/Steiner Tree algorithm to minimize total cable/pipe length.
    
    Args:
        assets: List of asset dicts with 'polygon' or centroid
        connection_point: Main utility connection point (gate/station)
        boundary: Optional boundary for constraint
        use_steiner: Use Steiner tree (slower but potentially shorter)
        
    Returns:
        InfrastructureResult with routed lines
    """
    if not assets:
        return InfrastructureResult(
            success=False,
            error="No assets to connect"
        )
    
    # Extract asset centroids
    asset_centroids = []
    for asset in assets:
        centroid = _extract_centroid(asset)
        if centroid:
            asset_centroids.append(centroid)
    
    if not asset_centroids:
        return InfrastructureResult(
            success=False,
            error="Could not extract asset centroids"
        )
    
    # Add connection point as first point
    all_points = [connection_point] + asset_centroids
    
    logger.info(f"Routing utilities for {len(asset_centroids)} assets")
    
    # Calculate MST or Steiner tree
    if use_steiner and boundary:
        # Generate candidate Steiner points along boundary
        steiner_candidates = _generate_steiner_candidates(boundary)
        edges = steiner_tree_approximation(
            terminal_points=all_points,
            grid_points=steiner_candidates
        )
        # Expand points list for Steiner candidates
        all_points = all_points + steiner_candidates
    else:
        edges = minimum_spanning_tree(all_points)
    
    # Convert edges to LineStrings
    lines = points_to_linestrings(all_points, edges)
    
    # Calculate total length
    total_length = sum(line.length for line in lines)
    
    # For simplicity, use same routing for electric and water
    # In practice, these might have different constraints
    return InfrastructureResult(
        success=True,
        electric_lines=lines,
        water_lines=lines.copy(),  # Same routing for now
        total_electric_length=total_length,
        total_water_length=total_length,
        connection_points=[connection_point]
    )


def route_along_boundary(
    assets: List[Dict[str, Any]],
    connection_point: Tuple[float, float],
    boundary: Polygon,
    offset_distance: float = 2.0
) -> InfrastructureResult:
    """Route utilities along boundary edges.
    
    Routes utilities along the perimeter of lot boundaries
    rather than direct lines.
    
    Args:
        assets: List of asset dicts
        connection_point: Main connection point
        boundary: Boundary polygon
        offset_distance: Distance from boundary edge
        
    Returns:
        InfrastructureResult
    """
    if boundary is None or boundary.is_empty:
        return InfrastructureResult(
            success=False,
            error="Boundary is required for perimeter routing"
        )
    
    # Create offset boundary for routing
    offset_boundary = boundary.buffer(-offset_distance)
    if offset_boundary.is_empty:
        offset_boundary = boundary
    
    # Extract centroids and connect to nearest boundary point
    lines = []
    
    for asset in assets:
        centroid = _extract_centroid(asset)
        if centroid:
            line = connect_to_edge(centroid, offset_boundary)
            if line:
                lines.append(line)
    
    # Connect all boundary points using MST along boundary
    # This is a simplified version - full implementation would
    # route along the boundary edges
    
    total_length = sum(line.length for line in lines)
    
    return InfrastructureResult(
        success=True,
        electric_lines=lines,
        water_lines=lines.copy(),
        total_electric_length=total_length,
        total_water_length=total_length,
        connection_points=[connection_point]
    )


def _extract_centroid(asset: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """Extract centroid from asset dict.
    
    Args:
        asset: Asset dict with polygon or centroid
        
    Returns:
        (x, y) centroid or None
    """
    # Try direct centroid
    if "centroid" in asset:
        c = asset["centroid"]
        return (c[0], c[1]) if len(c) >= 2 else None
    
    # Try polygon
    if "polygon" in asset:
        coords = asset["polygon"]
        if coords and len(coords) >= 3:
            try:
                poly = Polygon(coords)
                if poly.is_valid:
                    c = poly.centroid
                    return (c.x, c.y)
            except Exception:
                pass
    
    return None


def _generate_steiner_candidates(
    boundary: Polygon,
    num_points: int = 20
) -> List[Tuple[float, float]]:
    """Generate candidate Steiner points along boundary.
    
    Args:
        boundary: Boundary polygon
        num_points: Number of points to generate
        
    Returns:
        List of (x, y) coordinates
    """
    if boundary is None or boundary.is_empty:
        return []
    
    points = []
    perimeter = boundary.exterior.length
    step = perimeter / num_points
    
    for i in range(num_points):
        point = boundary.exterior.interpolate(i * step)
        points.append((point.x, point.y))
    
    return points
