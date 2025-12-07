"""
Voronoi diagram generation for road network planning.

Uses Shapely's Voronoi implementation to create organic road layouts
based on random seed points distributed within the site boundary.
"""

import random
import logging
from typing import List, Tuple, Optional

from shapely.geometry import Point, Polygon, MultiPoint, LineString
from shapely.ops import voronoi_diagram, unary_union

logger = logging.getLogger(__name__)


def generate_voronoi_seeds(
    site: Polygon,
    num_seeds: int = 15,
    seed: Optional[int] = None
) -> List[Point]:
    """
    Generate random seed points for Voronoi diagram.
    
    Points are uniformly distributed within the site bounding box.
    
    Args:
        site: Site boundary polygon
        num_seeds: Number of seed points to generate
        seed: Random seed for reproducibility (optional)
        
    Returns:
        List of Point objects
    """
    if seed is not None:
        random.seed(seed)
    
    minx, miny, maxx, maxy = site.bounds
    
    seeds = []
    for _ in range(num_seeds):
        x = random.uniform(minx, maxx)
        y = random.uniform(miny, maxy)
        seeds.append(Point(x, y))
    
    return seeds


def create_voronoi_diagram(
    seeds: List[Point],
    envelope: Polygon
) -> Optional[object]:
    """
    Create Voronoi diagram from seed points.
    
    Args:
        seeds: List of seed Point objects
        envelope: Bounding envelope for the diagram
        
    Returns:
        Voronoi regions geometry, or None if generation fails
    """
    if len(seeds) < 2:
        logger.warning("Need at least 2 seeds for Voronoi diagram")
        return None
    
    try:
        multi_point = MultiPoint(seeds)
        regions = voronoi_diagram(multi_point, envelope=envelope)
        return regions
    except Exception as e:
        logger.error(f"Voronoi diagram generation failed: {e}")
        return None


def extract_voronoi_edges(
    regions: object
) -> List[LineString]:
    """
    Extract edge LineStrings from Voronoi regions.
    
    Collects the exterior rings of all Voronoi cells and merges them.
    
    Args:
        regions: Voronoi diagram geometry (GeometryCollection of Polygons)
        
    Returns:
        List of LineString edges
    """
    edges = []
    
    if regions is None:
        return edges
    
    # Collect exterior rings from Voronoi polygons
    if hasattr(regions, 'geoms'):
        for region in regions.geoms:
            if region.geom_type == 'Polygon':
                edges.append(region.exterior)
    elif regions.geom_type == 'Polygon':
        edges.append(regions.exterior)
    
    if not edges:
        return []
    
    # Merge all lines for unified processing
    merged = unary_union(edges)
    
    # Normalize to list of LineStrings
    if hasattr(merged, 'geoms'):
        return [g for g in merged.geoms if g.geom_type == 'LineString']
    elif merged.geom_type == 'LineString':
        return [merged]
    else:
        return []


def classify_road_type(
    line: LineString,
    site_center: Point,
    center_threshold: float = 100.0,
    length_threshold: float = 400.0
) -> str:
    """
    Classify a road line as 'main' or 'internal'.
    
    Heuristic: Roads near center or very long are main roads.
    
    Args:
        line: Road centerline
        site_center: Center point of the site
        center_threshold: Distance threshold from center (m)
        length_threshold: Length threshold (m)
        
    Returns:
        'main' or 'internal'
    """
    dist_to_center = line.distance(site_center)
    
    if dist_to_center < center_threshold or line.length > length_threshold:
        return 'main'
    else:
        return 'internal'


def create_road_buffer(
    line: LineString,
    road_type: str,
    main_width: float = 30.0,
    internal_width: float = 15.0,
    sidewalk_width: float = 4.0
) -> Polygon:
    """
    Create road polygon by buffering centerline.
    
    Args:
        line: Road centerline
        road_type: 'main' or 'internal'
        main_width: Main road width (m)
        internal_width: Internal road width (m)
        sidewalk_width: Sidewalk width each side (m)
        
    Returns:
        Road polygon (buffered centerline)
    """
    if road_type == 'main':
        width = main_width + 2 * sidewalk_width
    else:
        width = internal_width + 2 * sidewalk_width
    
    # Use flat cap and mitre join for road-like appearance
    return line.buffer(width / 2, cap_style=2, join_style=2)
