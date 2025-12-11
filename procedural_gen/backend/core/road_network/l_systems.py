"""L-Systems road generator for organic branching patterns.

Generates road networks using Lindenmayer Systems (L-Systems) grammar.
Creates natural-looking road patterns with branching, similar to 
plant growth or urban organic development.

Reference: docs/Procedural Generation.md - Section 1
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import numpy as np
import logging
from shapely.geometry import Polygon, LineString, Point, MultiLineString
from shapely.ops import unary_union, linemerge

logger = logging.getLogger(__name__)


@dataclass
class LSystemConfig:
    """Configuration for L-System road generation."""
    
    # Axiom (starting symbol)
    axiom: str = "F"
    
    # Number of iterations (recursion depth)
    iterations: int = 3
    
    # Road segment length in meters
    step_length: float = 50.0
    
    # Branching angle in degrees
    angle: float = 30.0
    
    # Length reduction per iteration (0.0 - 1.0)
    length_decay: float = 0.8
    
    # Angle randomization range (+/- degrees)
    angle_variance: float = 10.0
    
    # Minimum road length to keep
    min_road_length: float = 30.0
    
    # Random seed for reproducibility
    seed: Optional[int] = None


# Predefined rule sets for different patterns
RULE_SETS = {
    # Industrial park: Regular branching with cul-de-sacs
    "industrial": {
        'F': 'FF+[+F-F-F]-[-F+F+F]',
        'X': 'F[+X][-X]FX'
    },
    
    # Residential: More organic, irregular branching
    "residential": {
        'F': 'F[+F]F[-F][F]',
        'X': 'F-[[X]+X]+F[+FX]-X'
    },
    
    # Grid-like: More structured pattern
    "grid": {
        'F': 'F+F-F-F+F',
        'X': 'FX+FX-FX'
    },
    
    # Spine: Main road with perpendicular branches
    "spine": {
        'F': 'FF',
        'X': 'F[+F]F[-F]X'
    }
}


class LSystemRoadGenerator:
    """Generate road networks using L-Systems grammar.
    
    L-System symbols:
    - F: Move forward, draw road segment
    - +: Turn left by angle
    - -: Turn right by angle  
    - [: Push current state (start branch)
    - ]: Pop state (end branch, return to saved position)
    
    Example:
        >>> generator = LSystemRoadGenerator(site_polygon)
        >>> roads = generator.generate()
    """
    
    def __init__(
        self,
        site_boundary: Polygon,
        config: Optional[LSystemConfig] = None,
        rules: Optional[Dict[str, str]] = None,
        rule_set: str = "industrial"
    ):
        """Initialize L-System road generator.
        
        Args:
            site_boundary: Site boundary polygon
            config: L-System configuration
            rules: Custom production rules (overrides rule_set)
            rule_set: Predefined rule set name
        """
        self.boundary = site_boundary
        self.config = config or LSystemConfig()
        
        # Use custom rules or predefined set
        if rules:
            self.rules = rules
        else:
            self.rules = RULE_SETS.get(rule_set, RULE_SETS["industrial"])
            
        # Setup random generator
        self.rng = np.random.default_rng(self.config.seed)
        
    def generate(
        self, 
        start_point: Optional[Point] = None,
        start_angle: Optional[float] = None
    ) -> List[LineString]:
        """Generate road network from L-System.
        
        Args:
            start_point: Starting point (defaults to boundary centroid)
            start_angle: Initial direction in degrees (defaults to 90 = up)
            
        Returns:
            List of road LineStrings
        """
        logger.info(f"Generating L-System roads with {self.config.iterations} iterations")
        
        # 1. Generate L-System string
        lstring = self._iterate_lsystem()
        logger.debug(f"L-System string length: {len(lstring)}")
        
        # 2. Interpret string as turtle graphics
        roads = self._interpret_lstring(lstring, start_point, start_angle)
        logger.debug(f"Generated {len(roads)} raw road segments")
        
        # 3. Clip to boundary
        clipped = self._clip_to_boundary(roads)
        logger.debug(f"After clipping: {len(clipped)} segments")
        
        # 4. Filter short segments
        filtered = [r for r in clipped if r.length >= self.config.min_road_length]
        logger.info(f"Final road count: {len(filtered)}")
        
        return filtered
        
    def generate_with_main_spine(
        self,
        spine_direction: Optional[np.ndarray] = None
    ) -> List[LineString]:
        """Generate roads with a main spine road through center.
        
        Creates a main road first, then branches from it.
        
        Args:
            spine_direction: Direction vector for main spine
            
        Returns:
            List of road LineStrings (first one is the main spine)
        """
        # Calculate main spine
        if spine_direction is None:
            # Use longest axis of bounding box
            minx, miny, maxx, maxy = self.boundary.bounds
            if (maxx - minx) > (maxy - miny):
                spine_direction = np.array([1, 0])
            else:
                spine_direction = np.array([0, 1])
                
        # Create main spine through center
        center = self.boundary.centroid
        diagonal = np.hypot(
            self.boundary.bounds[2] - self.boundary.bounds[0],
            self.boundary.bounds[3] - self.boundary.bounds[1]
        )
        
        p1 = np.array([center.x, center.y]) - spine_direction * diagonal
        p2 = np.array([center.x, center.y]) + spine_direction * diagonal
        
        main_spine = LineString([p1, p2])
        main_spine = main_spine.intersection(self.boundary)
        
        roads = []
        if main_spine.geom_type == 'LineString' and not main_spine.is_empty:
            roads.append(main_spine)
            
        # Generate branches from points along spine
        if main_spine.geom_type == 'LineString':
            branch_points = [
                main_spine.interpolate(t, normalized=True)
                for t in np.linspace(0.2, 0.8, 4)
            ]
            
            # Perpendicular direction
            perp = np.array([-spine_direction[1], spine_direction[0]])
            
            for point in branch_points:
                # Generate L-System branches from this point
                angle_deg = np.degrees(np.arctan2(perp[1], perp[0]))
                branch_roads = self.generate(
                    start_point=point,
                    start_angle=angle_deg
                )
                roads.extend(branch_roads[:3])  # Limit branches
                
        return roads
        
    def _iterate_lsystem(self) -> str:
        """Apply production rules iteratively.
        
        Returns:
            Final L-System string
        """
        result = self.config.axiom
        
        for i in range(self.config.iterations):
            new_result = ""
            for char in result:
                new_result += self.rules.get(char, char)
            result = new_result
            
        return result
        
    def _interpret_lstring(
        self, 
        lstring: str, 
        start: Optional[Point],
        start_angle: Optional[float]
    ) -> List[LineString]:
        """Convert L-System string to road geometry using turtle graphics.
        
        Args:
            lstring: L-System string to interpret
            start: Starting point
            start_angle: Initial direction (degrees)
            
        Returns:
            List of LineString road segments
        """
        # Starting position
        if start is None:
            start = self.boundary.centroid
            
        # Starting direction (default: up)
        if start_angle is None:
            start_angle = 90.0
            
        roads = []
        stack = []  # For branching (push/pop state)
        
        pos = np.array([start.x, start.y])
        angle = start_angle
        step = self.config.step_length
        depth = 0
        
        current_path = [pos.copy()]
        
        for char in lstring:
            if char == 'F':
                # Move forward, draw road
                rad = np.radians(angle)
                
                # Apply length decay based on depth
                current_step = step * (self.config.length_decay ** depth)
                
                new_pos = pos + current_step * np.array([np.cos(rad), np.sin(rad)])
                current_path.append(new_pos.copy())
                pos = new_pos
                
            elif char == '+':
                # Turn left
                variance = self.rng.uniform(
                    -self.config.angle_variance,
                    self.config.angle_variance
                )
                angle += self.config.angle + variance
                
            elif char == '-':
                # Turn right
                variance = self.rng.uniform(
                    -self.config.angle_variance,
                    self.config.angle_variance
                )
                angle -= self.config.angle + variance
                
            elif char == '[':
                # Push state (start branch)
                stack.append((pos.copy(), angle, step, list(current_path), depth))
                depth += 1
                current_path = [pos.copy()]
                
            elif char == ']':
                # Pop state (end branch)
                if len(current_path) >= 2:
                    roads.append(LineString(current_path))
                    
                if stack:
                    pos, angle, step, current_path, depth = stack.pop()
                else:
                    current_path = [pos.copy()]
                    depth = 0
                    
        # Don't forget the last path
        if len(current_path) >= 2:
            roads.append(LineString(current_path))
            
        return roads
        
    def _clip_to_boundary(self, roads: List[LineString]) -> List[LineString]:
        """Clip roads to site boundary.
        
        Args:
            roads: List of road LineStrings
            
        Returns:
            Clipped roads within boundary
        """
        clipped = []
        
        for road in roads:
            try:
                intersection = road.intersection(self.boundary)
                
                if intersection.is_empty:
                    continue
                    
                if intersection.geom_type == 'LineString':
                    clipped.append(intersection)
                elif intersection.geom_type == 'MultiLineString':
                    clipped.extend(list(intersection.geoms))
                    
            except Exception as e:
                logger.warning(f"Failed to clip road: {e}")
                continue
                
        return clipped


def generate_lsystem_roads(
    site_boundary: Polygon,
    rule_set: str = "industrial",
    iterations: int = 3,
    step_length: float = 50.0,
    angle: float = 30.0,
    seed: Optional[int] = None
) -> List[LineString]:
    """Convenience function to generate L-System roads.
    
    Args:
        site_boundary: Site boundary polygon
        rule_set: 'industrial', 'residential', 'grid', or 'spine'
        iterations: Number of L-System iterations
        step_length: Road segment length (m)
        angle: Branching angle (degrees)
        seed: Random seed
        
    Returns:
        List of road LineStrings
    """
    config = LSystemConfig(
        iterations=iterations,
        step_length=step_length,
        angle=angle,
        seed=seed
    )
    
    generator = LSystemRoadGenerator(
        site_boundary=site_boundary,
        config=config,
        rule_set=rule_set
    )
    
    return generator.generate()
