"""
REMB Unified Optimizer
Integrates all 3 algorithm fixes into a single interface

Components:
- FIX #1: GA with Order Crossover (SimpleGAOptimizer)
- FIX #2: NSGA-II with Hard Constraints (nsga2_constrained)
- FIX #3: A* Road Connectivity Validation (road_validator)

This module provides a high-level interface that:
1. Uses the appropriate optimizer based on complexity
2. Validates all solutions for road connectivity
3. Returns only feasible, validated layouts
"""
import logging
from typing import List, Dict, Tuple, Optional
from shapely.geometry import Polygon, box
import numpy as np

from src.algorithms.ga_optimizer import SimpleGAOptimizer
from src.algorithms.nsga2_constrained import (
    IndustrialEstateConstrainedProblem,
    solve_constrained_layout
)
from src.geometry.road_validator import (
    RoadConnectivityValidator,
    roads_to_grid,
    continuous_to_grid
)

logger = logging.getLogger(__name__)


class REMBOptimizer:
    """
    Unified Industrial Estate Optimizer
    
    Combines:
    - SimpleGA for fast MVP generation
    - NSGA-II for multi-objective optimization
    - A* for road connectivity validation
    
    Usage:
        optimizer = REMBOptimizer(
            site_boundary=site_polygon,
            buildable_area=buildable_polygon,
            roads=road_list,
            grid_size=(100, 100)
        )
        
        # Fast MVP mode
        mvp_options = optimizer.optimize_fast(target_plots=8)
        
        # Full optimization
        pareto_front = optimizer.optimize_full(
            n_plots=10,
            population_size=100,
            n_generations=100
        )
        
        # Validate any layout
        is_valid = optimizer.validate_layout(layout)
    """
    
    def __init__(
        self,
        site_boundary: Polygon,
        buildable_area: Polygon = None,
        roads: List[Dict] = None,
        grid_size: Tuple[int, int] = (100, 100),
        setback: float = 50.0
    ):
        """
        Args:
            site_boundary: Site boundary polygon
            buildable_area: Buildable area (optional, computed from setback)
            roads: List of road segments [{'start': (x,y), 'end': (x,y)}, ...]
            grid_size: Grid dimensions for A* validation
            setback: Setback distance from boundary (meters)
        """
        self.site_boundary = site_boundary
        self.setback = setback
        
        # Compute buildable area if not provided
        if buildable_area is None:
            self.buildable_area = site_boundary.buffer(-setback)
            if self.buildable_area.is_empty:
                logger.warning("Setback too large, reducing by half")
                self.buildable_area = site_boundary.buffer(-setback/2)
        else:
            self.buildable_area = buildable_area
        
        # Get bounds
        self.bounds = {
            'min_x': site_boundary.bounds[0],
            'min_y': site_boundary.bounds[1],
            'max_x': site_boundary.bounds[2],
            'max_y': site_boundary.bounds[3]
        }
        
        # Initialize road validator (FIX #3)
        self.roads = roads or []
        self.grid_size = grid_size
        self.road_validator = None
        
        if roads:
            road_cells = roads_to_grid(roads, self.bounds, grid_size)
            self.road_validator = RoadConnectivityValidator(
                grid_size=grid_size,
                road_cells=road_cells,
                cell_size=(self.bounds['max_x'] - self.bounds['min_x']) / grid_size[0]
            )
            logger.info(f"Road validator initialized: {len(road_cells)} road cells")
        
        logger.info(f"REMBOptimizer initialized")
        logger.info(f"  Site area: {site_boundary.area:.0f} m²")
        logger.info(f"  Buildable area: {self.buildable_area.area:.0f} m²")
    
    def optimize_fast(
        self,
        target_plots: int = 8,
        population_size: int = 10,
        n_generations: int = 20
    ) -> List[Dict]:
        """
        Fast optimization using improved GA (FIX #1)
        
        Returns 3 diverse layout options:
        1. Maximum Profit
        2. Balanced
        3. Premium
        
        Args:
            target_plots: Target number of plots
            population_size: GA population size
            n_generations: Number of generations
            
        Returns:
            List of 3 layout options
        """
        logger.info(f"Running fast GA optimization (FIX #1)")
        
        # Get boundary coordinates
        coords = list(self.site_boundary.exterior.coords)
        
        # Create optimizer with improved crossover
        optimizer = SimpleGAOptimizer(
            population_size=population_size,
            n_generations=n_generations,
            elite_size=3,
            mutation_rate=0.3,
            setback=self.setback,
            target_plots=target_plots
        )
        
        # Run optimization
        options = optimizer.optimize(coords)
        
        # Validate road access for each option
        for option in options:
            option['road_access_validated'] = self._validate_road_access(option['plots'])
        
        logger.info(f"Fast optimization complete: {len(options)} options")
        return options
    
    def optimize_full(
        self,
        n_plots: int = 10,
        population_size: int = 100,
        n_generations: int = 100,
        min_plot_size: float = 900,
        max_plot_size: float = 10000,
        seed: int = None
    ) -> Dict:
        """
        Full multi-objective optimization using NSGA-II with hard constraints (FIX #2)
        
        Args:
            n_plots: Number of plots
            population_size: NSGA-II population size
            n_generations: Number of generations  
            min_plot_size: Minimum plot area (m²)
            max_plot_size: Maximum plot area (m²)
            seed: Random seed
            
        Returns:
            Result dict with Pareto-optimal layouts
        """
        logger.info(f"Running full NSGA-II optimization (FIX #2)")
        
        result = solve_constrained_layout(
            site_boundary=self.site_boundary,
            buildable_area=self.buildable_area,
            n_plots=n_plots,
            population_size=population_size,
            n_generations=n_generations,
            min_plot_size=min_plot_size,
            max_plot_size=max_plot_size,
            seed=seed,
            verbose=False
        )
        
        # Validate road access for all feasible layouts
        if result['success'] and result['layouts']:
            validated_layouts = []
            for layout in result['layouts']:
                road_access = self._validate_layout_road_access(layout)
                validated_layouts.append({
                    'layout': layout,
                    'road_access': road_access,
                    'all_accessible': all(road_access.values()) if road_access else False
                })
            result['validated_layouts'] = validated_layouts
        
        logger.info(f"Full optimization complete")
        return result
    
    def validate_layout(self, layout: List[Dict]) -> Dict:
        """
        Validate a layout for constraints and road access
        
        Args:
            layout: List of plot dicts with x, y, width, height
            
        Returns:
            Validation result dict
        """
        result = {
            'is_valid': True,
            'has_overlaps': False,
            'all_contained': True,
            'all_road_access': True,
            'issues': []
        }
        
        # Check overlaps
        for i, p1 in enumerate(layout):
            geom1 = self._create_plot_geometry(p1)
            
            for j in range(i+1, len(layout)):
                p2 = layout[j]
                geom2 = self._create_plot_geometry(p2)
                
                if geom1.intersects(geom2):
                    result['has_overlaps'] = True
                    result['is_valid'] = False
                    result['issues'].append(f"Plots {i} and {j} overlap")
        
        # Check containment
        for i, p in enumerate(layout):
            geom = self._create_plot_geometry(p)
            if not self.buildable_area.contains(geom):
                result['all_contained'] = False
                result['is_valid'] = False
                result['issues'].append(f"Plot {i} outside buildable area")
        
        # Check road access (FIX #3)
        road_access = self._validate_layout_road_access(layout)
        if road_access:
            for i, accessible in road_access.items():
                if not accessible:
                    result['all_road_access'] = False
                    result['is_valid'] = False
                    result['issues'].append(f"Plot {i} cannot reach road")
        
        return result
    
    def _validate_road_access(self, plots: List[Dict]) -> Dict[int, bool]:
        """Validate road access for plots in frontend format"""
        if not self.road_validator:
            return {}
        
        results = {}
        for i, plot in enumerate(plots):
            # Convert to grid coordinates
            pos = continuous_to_grid(
                (plot['x'] + plot['width']/2, plot['y'] + plot['height']/2),
                self.bounds,
                self.grid_size
            )
            results[i] = self.road_validator.can_reach_road(pos)
        
        return results
    
    def _validate_layout_road_access(self, layout: List[Dict]) -> Dict[int, bool]:
        """Validate road access for internal layout format"""
        if not self.road_validator:
            return {}
        
        results = {}
        for plot in layout:
            pos = continuous_to_grid(
                (plot['x'], plot['y']),
                self.bounds,
                self.grid_size
            )
            results[plot.get('id', 0)] = self.road_validator.can_reach_road(pos)
        
        return results
    
    def _create_plot_geometry(self, plot: Dict) -> Polygon:
        """Create Shapely polygon from plot dict"""
        if 'coords' in plot:
            return Polygon(plot['coords'])
        
        x = plot.get('x', 0)
        y = plot.get('y', 0)
        w = plot.get('width', 50)
        h = plot.get('height', 50)
        
        # Check if x, y is corner or center
        # Frontend uses corner, internal uses center
        if 'width' in plot and 'height' in plot:
            return box(x, y, x + w, y + h)
        else:
            return box(x - w/2, y - h/2, x + w/2, y + h/2)


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create sample site
    site = box(0, 0, 500, 400)
    
    # Define roads
    roads = [
        {'start': (0, 200), 'end': (500, 200)},  # Horizontal
        {'start': (250, 0), 'end': (250, 400)},  # Vertical
    ]
    
    # Create optimizer
    optimizer = REMBOptimizer(
        site_boundary=site,
        roads=roads,
        setback=50,
        grid_size=(100, 80)
    )
    
    # Fast optimization
    print("\n" + "="*60)
    print("FAST OPTIMIZATION (GA with Crossover)")
    print("="*60)
    
    fast_options = optimizer.optimize_fast(target_plots=6)
    for opt in fast_options:
        print(f"  {opt['name']}: {opt['metrics']['total_plots']} plots, "
              f"{opt['metrics']['total_area']:.0f} m²")
    
    # Full optimization
    print("\n" + "="*60)
    print("FULL OPTIMIZATION (NSGA-II with Hard Constraints)")
    print("="*60)
    
    full_result = optimizer.optimize_full(
        n_plots=6,
        population_size=50,
        n_generations=50,
        seed=42
    )
    
    print(f"  Success: {full_result['success']}")
    print(f"  Pareto solutions: {full_result['n_solutions']}")
    print(f"  Feasible: {full_result['n_feasible']}")
    
    # Validate a layout
    if fast_options:
        validation = optimizer.validate_layout(fast_options[0]['plots'])
        print(f"\n  Validation of first layout:")
        print(f"    Valid: {validation['is_valid']}")
        print(f"    Overlaps: {validation['has_overlaps']}")
        print(f"    Road access: {validation['all_road_access']}")
