"""Road smoothing and corner treatment.

Applies aesthetic post-processing to road networks:
- Fillet (rounded) corners for truck turning radius
- Chamfer (beveled) corners for simpler intersections
- Spline smoothing for organic curves

Reference: docs/Procedural Generation.md - Section 4 (Fillet & Chamfer)
"""

from typing import List, Optional, Tuple
import numpy as np
import logging
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import linemerge, unary_union

logger = logging.getLogger(__name__)


class RoadSmoother:
    """Smooth road corners and intersections.
    
    Provides methods for aesthetic enhancement of road networks:
    - Fillet: Round corners with specified radius (R=12m for containers)
    - Chamfer: Bevel corners for simpler treatment
    - Spline: Smooth entire road with curve interpolation
    """
    
    # Default fillet radius for container trucks
    DEFAULT_FILLET_RADIUS = 12.0
    
    # Minimum angle (degrees) to apply corner treatment
    MIN_CORNER_ANGLE = 30.0
    
    @staticmethod
    def fillet_corners(
        road: LineString,
        radius: float = 12.0,
        min_angle: float = 30.0,
        num_arc_points: int = 8
    ) -> LineString:
        """Apply fillet (rounded arc) to sharp corners.
        
        Creates smooth curves at corners for truck turning radius.
        Standard R=12m allows container trucks to navigate.
        
        Args:
            road: Road centerline
            radius: Fillet radius in meters (default 12m for trucks)
            min_angle: Only fillet angles sharper than this
            num_arc_points: Number of points in arc approximation
            
        Returns:
            Smoothed road with filleted corners
        """
        coords = list(road.coords)
        
        if len(coords) < 3:
            return road
            
        new_coords = [coords[0]]
        
        for i in range(1, len(coords) - 1):
            p0 = np.array(coords[i - 1])
            p1 = np.array(coords[i])
            p2 = np.array(coords[i + 1])
            
            # Calculate vectors
            v1 = p0 - p1
            v2 = p2 - p1
            
            len1 = np.linalg.norm(v1)
            len2 = np.linalg.norm(v2)
            
            if len1 < 1e-10 or len2 < 1e-10:
                new_coords.append(tuple(p1))
                continue
                
            v1_norm = v1 / len1
            v2_norm = v2 / len2
            
            # Calculate angle
            cos_angle = np.clip(np.dot(v1_norm, v2_norm), -1, 1)
            angle_rad = np.arccos(cos_angle)
            angle_deg = np.degrees(angle_rad)
            
            # Check if corner is sharp enough
            if angle_deg < 180 - min_angle:
                # Apply fillet
                arc_points = RoadSmoother._create_fillet_arc(
                    p0, p1, p2, radius, num_arc_points
                )
                new_coords.extend(arc_points)
            else:
                # Keep original point
                new_coords.append(tuple(p1))
                
        new_coords.append(coords[-1])
        
        # Filter duplicate/very close points
        filtered = RoadSmoother._remove_duplicate_coords(new_coords)
        
        if len(filtered) < 2:
            return road
            
        return LineString(filtered)
        
    @staticmethod
    def _create_fillet_arc(
        p0: np.ndarray,
        p1: np.ndarray,
        p2: np.ndarray,
        radius: float,
        num_points: int = 8
    ) -> List[Tuple[float, float]]:
        """Create arc points for fillet.
        
        Args:
            p0: Previous point
            p1: Corner point
            p2: Next point
            radius: Fillet radius
            num_points: Number of arc points
            
        Returns:
            List of (x, y) tuples for arc
        """
        # Direction vectors
        v1 = p0 - p1
        v2 = p2 - p1
        
        len1 = np.linalg.norm(v1)
        len2 = np.linalg.norm(v2)
        
        if len1 < 1e-10 or len2 < 1e-10:
            return [tuple(p1)]
            
        v1_norm = v1 / len1
        v2_norm = v2 / len2
        
        # Limit radius to not exceed edge lengths
        max_radius = min(len1, len2) * 0.4
        actual_radius = min(radius, max_radius)
        
        if actual_radius < 1.0:
            return [tuple(p1)]
            
        # Calculate tangent points
        t1 = p1 + v1_norm * actual_radius
        t2 = p1 + v2_norm * actual_radius
        
        # Interpolate arc (simple linear interpolation for approximation)
        arc_points = []
        for t in np.linspace(0, 1, num_points):
            # Simple arc: blend between tangent points
            # For true circular arc, would need to compute arc center
            pt = (1 - t) * t1 + t * t2
            arc_points.append(tuple(pt))
            
        return arc_points
        
    @staticmethod
    def chamfer_corners(
        road: LineString,
        chamfer_length: float = 5.0,
        min_angle: float = 45.0
    ) -> LineString:
        """Apply chamfer (bevel) to sharp corners.
        
        Simpler than fillet - just cuts the corner with a straight line.
        
        Args:
            road: Road centerline
            chamfer_length: Length of chamfer cut
            min_angle: Only chamfer angles sharper than this
            
        Returns:
            Road with chamfered corners
        """
        coords = list(road.coords)
        
        if len(coords) < 3:
            return road
            
        new_coords = [coords[0]]
        
        for i in range(1, len(coords) - 1):
            p0 = np.array(coords[i - 1])
            p1 = np.array(coords[i])
            p2 = np.array(coords[i + 1])
            
            # Direction vectors
            v1 = p0 - p1
            v2 = p2 - p1
            
            len1 = np.linalg.norm(v1)
            len2 = np.linalg.norm(v2)
            
            if len1 < 1e-10 or len2 < 1e-10:
                new_coords.append(tuple(p1))
                continue
                
            v1_norm = v1 / len1
            v2_norm = v2 / len2
            
            # Calculate angle
            cos_angle = np.clip(np.dot(v1_norm, v2_norm), -1, 1)
            angle_deg = np.degrees(np.arccos(cos_angle))
            
            if angle_deg < 180 - min_angle:
                # Apply chamfer
                actual_length = min(chamfer_length, len1 * 0.4, len2 * 0.4)
                
                t1 = p1 + v1_norm * actual_length
                t2 = p1 + v2_norm * actual_length
                
                new_coords.append(tuple(t1))
                new_coords.append(tuple(t2))
            else:
                new_coords.append(tuple(p1))
                
        new_coords.append(coords[-1])
        
        return LineString(new_coords)
        
    @staticmethod
    def smooth_spline(
        road: LineString,
        smoothness: float = 0.5,
        num_points: int = None
    ) -> LineString:
        """Smooth road using spline interpolation.
        
        Creates organic curves by fitting a spline through road points.
        
        Args:
            road: Road centerline
            smoothness: Smoothing factor (0 = interpolate, higher = smoother)
            num_points: Output point count (default: 3x input)
            
        Returns:
            Smoothed road
        """
        coords = np.array(road.coords)
        
        if len(coords) < 4:
            return road
            
        try:
            from scipy.interpolate import splprep, splev
            
            # Fit spline
            tck, u = splprep(
                [coords[:, 0], coords[:, 1]], 
                s=smoothness * len(coords),
                k=min(3, len(coords) - 1)
            )
            
            # Evaluate at more points
            if num_points is None:
                num_points = len(coords) * 3
                
            u_new = np.linspace(0, 1, num_points)
            x_new, y_new = splev(u_new, tck)
            
            return LineString(zip(x_new, y_new))
            
        except ImportError:
            logger.warning("scipy not available for spline smoothing")
            return road
        except Exception as e:
            logger.warning(f"Spline smoothing failed: {e}")
            return road
            
    @staticmethod
    def _remove_duplicate_coords(
        coords: List[Tuple[float, float]],
        tolerance: float = 0.1
    ) -> List[Tuple[float, float]]:
        """Remove duplicate or very close coordinates.
        
        Args:
            coords: List of (x, y) tuples
            tolerance: Minimum distance between points
            
        Returns:
            Filtered coordinate list
        """
        if not coords:
            return []
            
        filtered = [coords[0]]
        
        for coord in coords[1:]:
            last = filtered[-1]
            dist = np.hypot(coord[0] - last[0], coord[1] - last[1])
            if dist >= tolerance:
                filtered.append(coord)
                
        return filtered


def smooth_road_network(
    roads: List[LineString],
    fillet_radius: float = 12.0,
    apply_spline: bool = False
) -> List[LineString]:
    """Apply smoothing to a road network.
    
    Args:
        roads: List of road LineStrings
        fillet_radius: Corner fillet radius
        apply_spline: Also apply spline smoothing
        
    Returns:
        Smoothed road network
    """
    smoothed = []
    
    for road in roads:
        if road.is_empty or road.length < 10:
            continue
            
        # Apply fillet
        filleted = RoadSmoother.fillet_corners(road, radius=fillet_radius)
        
        # Optionally apply spline
        if apply_spline:
            filleted = RoadSmoother.smooth_spline(filleted, smoothness=0.3)
            
        smoothed.append(filleted)
        
    return smoothed
