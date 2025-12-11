"""Road Network generation module.

Contains algorithms for generating organic road networks:
- L-Systems for branching patterns
- Skeletonization for central main roads
- Road smoothing and corner treatment
"""

from typing import List, Optional
import logging
from shapely.geometry import Polygon, LineString

from .l_systems import LSystemRoadGenerator, LSystemConfig, generate_lsystem_roads
from .skeletonization import SkeletonRoadGenerator, SkeletonConfig, generate_skeleton_roads
from .road_smoother import RoadSmoother, smooth_road_network

logger = logging.getLogger(__name__)


def generate_road_network(
    site_boundary: Polygon,
    algorithm: str = "skeleton",
    fillet_radius: float = 12.0,
    **kwargs
) -> List[LineString]:
    """Generate road network for the site.
    
    Args:
        site_boundary: Site boundary polygon
        algorithm: 'skeleton', 'l_systems', or 'hybrid'
        fillet_radius: Corner fillet radius (m)
        **kwargs: Additional algorithm-specific parameters
        
    Returns:
        List of road centerlines as LineStrings
    """
    logger.info(f"Generating road network using '{algorithm}' algorithm")
    
    roads = []
    
    if algorithm == "skeleton":
        # Use skeletonization for main roads
        roads = generate_skeleton_roads(
            site_boundary=site_boundary,
            include_branches=kwargs.get('include_branches', True),
            num_branches=kwargs.get('num_branches', 4)
        )
        
    elif algorithm == "l_systems":
        # Use L-Systems for organic branching
        roads = generate_lsystem_roads(
            site_boundary=site_boundary,
            rule_set=kwargs.get('rule_set', 'industrial'),
            iterations=kwargs.get('iterations', 3),
            step_length=kwargs.get('step_length', 50.0),
            angle=kwargs.get('angle', 30.0),
            seed=kwargs.get('seed', None)
        )
        
    elif algorithm == "hybrid":
        # Hybrid: Skeleton for main + L-Systems for secondary
        skeleton_gen = SkeletonRoadGenerator(site_boundary)
        main_road = skeleton_gen.generate_main_road()
        
        if main_road and not main_road.is_empty:
            roads.append(main_road)
            
        # Generate L-System branches from points along main road
        if main_road and main_road.length > 50:
            lsys_gen = LSystemRoadGenerator(
                site_boundary,
                config=LSystemConfig(iterations=2, step_length=30.0)
            )
            
            # Generate from multiple start points
            for t in [0.25, 0.5, 0.75]:
                start_point = main_road.interpolate(t, normalized=True)
                branch_roads = lsys_gen.generate(start_point=start_point)
                roads.extend(branch_roads[:2])  # Limit branches
                
    else:
        logger.warning(f"Unknown algorithm '{algorithm}', using skeleton")
        roads = generate_skeleton_roads(site_boundary)
        
    # Apply fillet smoothing to all roads
    if fillet_radius > 0 and roads:
        roads = smooth_road_network(roads, fillet_radius=fillet_radius)
        
    # Filter out empty or too short roads
    min_length = kwargs.get('min_road_length', 30.0)
    roads = [r for r in roads if r and not r.is_empty and r.length >= min_length]
    
    logger.info(f"Generated {len(roads)} roads")
    
    return roads


__all__ = [
    "generate_road_network",
    "LSystemRoadGenerator",
    "LSystemConfig", 
    "generate_lsystem_roads",
    "SkeletonRoadGenerator",
    "SkeletonConfig",
    "generate_skeleton_roads",
    "RoadSmoother",
    "smooth_road_network"
]
