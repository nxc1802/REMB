"""Medial axis transform for central main road generation.

Uses skeletonization to find the central axis of the site polygon,
creating main roads that are equidistant from all edges.

Reference: docs/Procedural Generation.md - Section 1 (Skeletonization)
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np
import logging
from shapely.geometry import Polygon, LineString, MultiLineString, Point
from shapely.ops import linemerge, unary_union

logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    from scipy.ndimage import distance_transform_edt
    from skimage.morphology import skeletonize, medial_axis
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False
    logger.warning("scikit-image not available, using simplified skeleton")


@dataclass
class SkeletonConfig:
    """Configuration for skeleton road generation."""
    
    # Rasterization resolution (meters per pixel)
    resolution: float = 2.0
    
    # Minimum road segment length to keep
    min_road_length: float = 30.0
    
    # Simplification tolerance (meters)
    simplify_tolerance: float = 5.0
    
    # Prune short branches (fraction of longest path)
    prune_ratio: float = 0.1
    
    # Road buffer width for secondary roads (meters)
    secondary_road_buffer: float = 50.0


class SkeletonRoadGenerator:
    """Generate main roads along polygon's medial axis.
    
    The medial axis (skeleton) is the set of points equidistant from 
    multiple edges of the polygon. This creates natural central roads
    that divide the site evenly.
    
    Algorithm:
    1. Rasterize polygon to binary image
    2. Compute medial axis (skeleton)
    3. Vectorize skeleton to LineStrings
    4. Prune short branches
    5. Simplify and smooth
    
    Example:
        >>> generator = SkeletonRoadGenerator(site_polygon)
        >>> main_road = generator.generate_main_road()
        >>> all_roads = generator.generate_road_network()
    """
    
    def __init__(
        self,
        site_boundary: Polygon,
        config: Optional[SkeletonConfig] = None
    ):
        """Initialize skeleton road generator.
        
        Args:
            site_boundary: Site boundary polygon
            config: Skeleton configuration
        """
        self.boundary = site_boundary
        self.config = config or SkeletonConfig()
        
        # Precompute bounds
        self.minx, self.miny, self.maxx, self.maxy = site_boundary.bounds
        
    def generate_main_road(self) -> LineString:
        """Generate the main central road from skeleton.
        
        Returns the longest continuous path through the skeleton,
        which represents the primary axis of the site.
        
        Returns:
            Main road centerline as LineString
        """
        logger.info("Generating main road from skeleton")
        
        skeleton_lines = self._compute_skeleton_lines()
        
        if not skeleton_lines:
            logger.warning("No skeleton lines generated, using centroid line")
            return self._fallback_centroid_line()
            
        # Find the longest path
        main_road = max(skeleton_lines, key=lambda l: l.length)
        
        # Simplify for smoother road
        main_road = main_road.simplify(self.config.simplify_tolerance)
        
        logger.info(f"Main road length: {main_road.length:.1f}m")
        
        return main_road
        
    def generate_road_network(self) -> List[LineString]:
        """Generate complete road network from skeleton.
        
        Includes main road plus significant branches.
        
        Returns:
            List of road LineStrings
        """
        logger.info("Generating road network from skeleton")
        
        skeleton_lines = self._compute_skeleton_lines()
        
        if not skeleton_lines:
            return [self._fallback_centroid_line()]
            
        # Filter by minimum length
        min_len = self.config.min_road_length
        filtered = [l for l in skeleton_lines if l.length >= min_len]
        
        # Prune based on ratio to longest
        if filtered:
            max_length = max(l.length for l in filtered)
            threshold = max_length * self.config.prune_ratio
            pruned = [l for l in filtered if l.length >= threshold]
        else:
            pruned = filtered
            
        # Simplify all roads
        simplified = [
            l.simplify(self.config.simplify_tolerance) 
            for l in pruned
        ]
        
        logger.info(f"Generated {len(simplified)} skeleton roads")
        
        return simplified
        
    def generate_with_perpendicular_branches(
        self,
        num_branches: int = 4,
        branch_spacing: float = 100.0
    ) -> List[LineString]:
        """Generate main road with perpendicular branch roads.
        
        Creates a spine road with evenly-spaced perpendicular branches,
        similar to a fishbone pattern.
        
        Args:
            num_branches: Number of perpendicular branches
            branch_spacing: Minimum spacing between branches (m)
            
        Returns:
            List of road LineStrings
        """
        roads = []
        
        # Get main road
        main_road = self.generate_main_road()
        roads.append(main_road)
        
        if main_road.is_empty or main_road.length < branch_spacing:
            return roads
            
        # Calculate branch points along main road
        num_points = min(num_branches, int(main_road.length / branch_spacing))
        
        for i in range(1, num_points + 1):
            t = i / (num_points + 1)
            
            # Get point and tangent
            point = main_road.interpolate(t, normalized=True)
            
            # Get direction at this point
            nearby_t = min(1.0, t + 0.01)
            nearby_point = main_road.interpolate(nearby_t, normalized=True)
            
            direction = np.array([
                nearby_point.x - point.x,
                nearby_point.y - point.y
            ])
            
            if np.linalg.norm(direction) > 0:
                direction = direction / np.linalg.norm(direction)
            else:
                direction = np.array([1, 0])
                
            # Perpendicular direction
            perp = np.array([-direction[1], direction[0]])
            
            # Create branch in both directions
            diagonal = np.hypot(
                self.maxx - self.minx,
                self.maxy - self.miny
            )
            
            branch_line = LineString([
                (point.x - perp[0] * diagonal, point.y - perp[1] * diagonal),
                (point.x + perp[0] * diagonal, point.y + perp[1] * diagonal)
            ])
            
            # Clip to boundary
            clipped = branch_line.intersection(self.boundary)
            
            if clipped.geom_type == 'LineString' and not clipped.is_empty:
                if clipped.length >= self.config.min_road_length:
                    roads.append(clipped)
            elif clipped.geom_type == 'MultiLineString':
                for segment in clipped.geoms:
                    if segment.length >= self.config.min_road_length:
                        roads.append(segment)
                        
        return roads
        
    def _compute_skeleton_lines(self) -> List[LineString]:
        """Compute skeleton and convert to LineStrings.
        
        Returns:
            List of skeleton LineStrings
        """
        if HAS_SKIMAGE:
            return self._compute_skeleton_skimage()
        else:
            return self._compute_skeleton_simple()
            
    def _compute_skeleton_skimage(self) -> List[LineString]:
        """Compute skeleton using scikit-image.
        
        Returns:
            List of skeleton LineStrings
        """
        # Calculate raster dimensions
        width = int((self.maxx - self.minx) / self.config.resolution) + 1
        height = int((self.maxy - self.miny) / self.config.resolution) + 1
        
        # Limit size for performance
        max_size = 1000
        if width > max_size or height > max_size:
            scale = max_size / max(width, height)
            width = int(width * scale)
            height = int(height * scale)
            actual_resolution = (self.maxx - self.minx) / width
        else:
            actual_resolution = self.config.resolution
            
        logger.debug(f"Rasterizing to {width}x{height} pixels")
        
        # Create binary mask
        mask = np.zeros((height, width), dtype=bool)
        
        for i in range(height):
            for j in range(width):
                x = self.minx + j * actual_resolution
                y = self.miny + i * actual_resolution
                if self.boundary.contains(Point(x, y)):
                    mask[i, j] = True
                    
        # Compute skeleton
        skeleton = skeletonize(mask)
        
        # Convert back to world coordinates
        return self._skeleton_to_lines(skeleton, actual_resolution)
        
    def _compute_skeleton_simple(self) -> List[LineString]:
        """Simple skeleton approximation without scikit-image.
        
        For rectangular and simple polygons, creates axis-aligned
        skeleton lines. For complex polygons, uses erosion approach.
        
        Returns:
            List of skeleton LineStrings
        """
        logger.debug("Using simplified skeleton (axis-based)")
        
        lines = []
        center = self.boundary.centroid
        width = self.maxx - self.minx
        height = self.maxy - self.miny
        
        # For rectangular or near-rectangular shapes,
        # create main axis along the longer dimension
        
        if width > height * 1.2:
            # Predominantly horizontal: create horizontal skeleton
            main_line = LineString([
                (self.minx + width * 0.02, center.y),
                (self.minx + width * 0.98, center.y)
            ])
        elif height > width * 1.2:
            # Predominantly vertical: create vertical skeleton
            main_line = LineString([
                (center.x, self.miny + height * 0.02),
                (center.x, self.miny + height * 0.98)
            ])
        else:
            # Square-ish: create diagonal or cross
            main_line = LineString([
                (self.minx + width * 0.02, center.y),
                (self.minx + width * 0.98, center.y)
            ])
            
        # Clip to boundary
        clipped = main_line.intersection(self.boundary)
        
        if clipped.geom_type == 'LineString' and not clipped.is_empty:
            lines.append(clipped)
        elif clipped.geom_type == 'MultiLineString':
            for segment in clipped.geoms:
                if segment.length > 10:
                    lines.append(segment)
                    
        # For more complex polygons, also try erosion-based approach
        if self.boundary.exterior.coords and len(list(self.boundary.exterior.coords)) > 5:
            # Polygon has many vertices - try to trace through erosion
            erosion_lines = self._trace_erosion_skeleton()
            if erosion_lines:
                lines.extend(erosion_lines)
                
        return lines
        
    def _trace_erosion_skeleton(self) -> List[LineString]:
        """Trace skeleton by sampling points along eroded boundaries.
        
        Returns:
            List of skeleton LineStrings
        """
        lines = []
        width = self.maxx - self.minx
        height = self.maxy - self.miny
        
        # Sample points along multiple erosion levels
        erosion_levels = [0.1, 0.2, 0.3, 0.4]  # Fraction of min dimension
        min_dim = min(width, height)
        
        sampled_points = []
        
        for level in erosion_levels:
            erosion_dist = min_dim * level
            eroded = self.boundary.buffer(-erosion_dist)
            
            if eroded.is_empty:
                continue
                
            if eroded.geom_type == 'MultiPolygon':
                eroded = max(eroded.geoms, key=lambda g: g.area)
                
            # Sample centroid at this level
            sampled_points.append(eroded.centroid)
            
        # Create line through sampled points
        if len(sampled_points) >= 2:
            # Check if points form a meaningful line (not clustered)
            coords = [(p.x, p.y) for p in sampled_points]
            
            # Calculate spread
            xs = [c[0] for c in coords]
            ys = [c[1] for c in coords]
            spread = max(max(xs) - min(xs), max(ys) - min(ys))
            
            if spread > min_dim * 0.05:  # Minimum 5% spread
                lines.append(LineString(coords))
                
        return lines
        
    def _skeleton_to_lines(
        self, 
        skeleton: np.ndarray,
        resolution: float
    ) -> List[LineString]:
        """Convert skeleton raster to LineStrings.
        
        Args:
            skeleton: Binary skeleton array
            resolution: Pixel resolution in meters
            
        Returns:
            List of LineStrings
        """
        # Find skeleton pixel coordinates
        y_coords, x_coords = np.where(skeleton)
        
        if len(x_coords) == 0:
            return []
            
        # Convert to world coordinates
        world_coords = [
            (self.minx + x * resolution, self.miny + y * resolution)
            for x, y in zip(x_coords, y_coords)
        ]
        
        # Simple approach: Connect nearby points into line segments
        # For better results, use graph-based tracing
        
        if len(world_coords) < 2:
            return []
            
        # Sort by x then y to create somewhat ordered line
        sorted_coords = sorted(world_coords, key=lambda c: (c[0], c[1]))
        
        # Create single line (simplified approach)
        # A more sophisticated approach would trace connected components
        line = LineString(sorted_coords)
        
        # Simplify to reduce zigzag
        simplified = line.simplify(resolution * 2)
        
        return [simplified]
        
    def _fallback_centroid_line(self) -> LineString:
        """Create a simple line through centroid as fallback.
        
        Returns:
            LineString through site center
        """
        center = self.boundary.centroid
        
        # Create line along longer axis
        width = self.maxx - self.minx
        height = self.maxy - self.miny
        
        if width > height:
            # Horizontal line
            return LineString([
                (self.minx + width * 0.1, center.y),
                (self.minx + width * 0.9, center.y)
            ]).intersection(self.boundary)
        else:
            # Vertical line
            return LineString([
                (center.x, self.miny + height * 0.1),
                (center.x, self.miny + height * 0.9)
            ]).intersection(self.boundary)


def generate_skeleton_roads(
    site_boundary: Polygon,
    resolution: float = 2.0,
    min_road_length: float = 30.0,
    include_branches: bool = True,
    num_branches: int = 4
) -> List[LineString]:
    """Convenience function to generate skeleton-based roads.
    
    Args:
        site_boundary: Site boundary polygon
        resolution: Rasterization resolution (m/pixel)
        min_road_length: Minimum road length to keep (m)
        include_branches: Include perpendicular branches
        num_branches: Number of perpendicular branches
        
    Returns:
        List of road LineStrings
    """
    config = SkeletonConfig(
        resolution=resolution,
        min_road_length=min_road_length
    )
    
    generator = SkeletonRoadGenerator(
        site_boundary=site_boundary,
        config=config
    )
    
    if include_branches:
        return generator.generate_with_perpendicular_branches(
            num_branches=num_branches
        )
    else:
        return generator.generate_road_network()
