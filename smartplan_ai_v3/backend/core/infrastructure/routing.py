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
    connect_to_edge,
    loop_network_mst,
    kmeans_transformer_placement,
    calculate_drainage_flow
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
    # Enhanced fields
    transformers: List[Tuple[float, float]] = field(default_factory=list)
    drainage_arrows: List[Dict[str, Any]] = field(default_factory=list)
    redundant_edges: int = 0
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
        
        # Add transformers as points
        for i, pos in enumerate(self.transformers):
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [pos[0], pos[1]]},
                "properties": {
                    "type": "transformer",
                    "id": f"T{i+1}"
                }
            })
        
        # Add drainage arrows as lines
        for i, arrow in enumerate(self.drainage_arrows):
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [arrow['start'][0], arrow['start'][1]],
                        [arrow['end'][0], arrow['end'][1]]
                    ]
                },
                "properties": {
                    "type": "drainage",
                    "id": f"D{i+1}"
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
    
    # Filter out roads - they don't need electric/water
    EXCLUDED_TYPES = {'internal_road', 'road', 'main_road'}
    building_assets = [a for a in assets if a.get('type', '') not in EXCLUDED_TYPES]
    
    if not building_assets:
        return InfrastructureResult(
            success=False,
            error="No buildings to connect (only roads found)"
        )
    
    # Extract asset centroids from buildings only
    asset_centroids = []
    for asset in building_assets:
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


def route_utilities_enhanced(
    assets: List[Dict[str, Any]],
    connection_point: Tuple[float, float],
    boundary: Polygon = None,
    use_loop_network: bool = True,
    redundancy_ratio: float = 0.15,
    add_transformers: bool = True,
    add_drainage: bool = True,
    drainage_outlet: Tuple[float, float] = None
) -> InfrastructureResult:
    """Enhanced utility routing with loop network, transformers, and drainage.
    
    Uses MST with redundancy for electrical network reliability,
    K-Means for transformer placement, and gravity-based drainage flow.
    
    Args:
        assets: List of asset dicts with 'polygon' or centroid
        connection_point: Main utility connection point (gate/station)
        boundary: Optional boundary polygon
        use_loop_network: Add redundant edges for reliability (default True)
        redundancy_ratio: Extra edges to add (0.0-1.0), default 15%
        add_transformers: Calculate optimal transformer positions
        add_drainage: Calculate drainage flow directions
        drainage_outlet: Drainage outlet point (defaults to connection_point)
        
    Returns:
        InfrastructureResult with enhanced routing
    """
    if not assets:
        return InfrastructureResult(
            success=False,
            error="No assets to connect"
        )
    
    # Filter out roads - they don't need electric/water
    EXCLUDED_TYPES = {'internal_road', 'road', 'main_road'}
    building_assets = [a for a in assets if a.get('type', '') not in EXCLUDED_TYPES]
    
    if not building_assets:
        return InfrastructureResult(
            success=False,
            error="No buildings to connect (only roads found)"
        )
    
    logger.info(f"Filtering assets: {len(assets)} total -> {len(building_assets)} buildings (excluding roads)")
    
    # Extract asset centroids from buildings only
    asset_centroids = []
    for asset in building_assets:
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
    
    logger.info(f"Enhanced routing for {len(asset_centroids)} buildings")
    
    # Calculate edges using loop network or MST
    if use_loop_network:
        edges = loop_network_mst(all_points, redundancy_ratio=redundancy_ratio)
        # Count redundant edges (more than MST would have)
        mst_edges = len(all_points) - 1
        redundant = len(edges) - mst_edges
    else:
        edges = minimum_spanning_tree(all_points)
        redundant = 0
    
    # Convert edges to LineStrings
    electric_lines = points_to_linestrings(all_points, edges)
    water_lines = points_to_linestrings(all_points, minimum_spanning_tree(all_points))
    
    # Calculate total lengths
    total_electric = sum(line.length for line in electric_lines)
    total_water = sum(line.length for line in water_lines)
    
    # Transformer placement
    transformers = []
    if add_transformers and len(asset_centroids) >= 2:
        transformers = kmeans_transformer_placement(asset_centroids, lots_per_transformer=10)
    
    # Drainage flow
    drainage_arrows = []
    if add_drainage:
        outlet = drainage_outlet or connection_point
        drainage_arrows = calculate_drainage_flow(asset_centroids, outlet)
    
    return InfrastructureResult(
        success=True,
        electric_lines=electric_lines,
        water_lines=water_lines,
        total_electric_length=total_electric,
        total_water_length=total_water,
        connection_points=[connection_point],
        transformers=transformers,
        drainage_arrows=drainage_arrows,
        redundant_edges=redundant
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
