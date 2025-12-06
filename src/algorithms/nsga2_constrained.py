"""
NSGA-II with Hard Constraints for Industrial Estate Optimization
FIX #2: Convert soft constraints to hard constraints

Academic Reference:
- Deb, K., et al. (2002). "A fast and elitist multiobjective genetic 
  algorithm: NSGA-II". IEEE Trans. on Evolutionary Computation.
- Pymoo documentation: pymoo.org/constraints

Key Difference from Original:
- Original: Overlap penalty as 5th objective (soft constraint)
- Fixed: Overlap as hard constraint using out["G"] (MUST NOT violate)
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

from pymoo.core.problem import Problem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM

from shapely.geometry import Polygon, box

logger = logging.getLogger(__name__)


class IndustrialEstateConstrainedProblem(Problem):
    """
    Multi-Objective Industrial Estate Layout Optimization with Hard Constraints
    
    Objectives (minimize):
    1. -Sellable area (maximize by negating)
    2. -Green space (maximize by negating)
    3. Road network length
    
    Hard Constraints (MUST NOT VIOLATE) - using out["G"]:
    1. No plot overlaps (g <= 0 means violation)
    2. All plots within buildable area
    3. Minimum plot separation (10m buffer)
    
    Variables per plot:
    - x, y: Position (normalized 0-1)
    - width, height: Dimensions (meters)
    """
    
    def __init__(
        self,
        site_boundary: Polygon,
        buildable_area: Polygon,
        n_plots: int = 10,
        min_plot_size: float = 900,  # 30m x 30m
        max_plot_size: float = 10000,  # 100m x 100m
        min_separation: float = 10.0,  # 10m between plots
        road_validator = None,
        **kwargs
    ):
        """
        Args:
            site_boundary: Overall site polygon
            buildable_area: Buildable polygon (after setbacks)
            n_plots: Target number of plots
            min_plot_size: Minimum plot area in m²
            max_plot_size: Maximum plot area in m²
            min_separation: Minimum distance between plots
            road_validator: Optional RoadConnectivityValidator
        """
        self.site_boundary = site_boundary
        self.buildable_area = buildable_area
        self.n_plots = n_plots
        self.min_plot_size = min_plot_size
        self.max_plot_size = max_plot_size
        self.min_separation = min_separation
        self.road_validator = road_validator
        
        # Get bounds
        self.bounds = buildable_area.bounds  # (minx, miny, maxx, maxy)
        
        # 4 variables per plot: x, y, width, height
        n_var = n_plots * 4
        
        # Number of constraints:
        # - n_plots * (n_plots - 1) / 2 overlap constraints
        # - n_plots containment constraints
        n_overlap = int(n_plots * (n_plots - 1) / 2)
        n_containment = n_plots
        n_constr = n_overlap + n_containment
        
        # Variable bounds
        minx, miny, maxx, maxy = self.bounds
        width_range = maxx - minx
        height_range = maxy - miny
        
        # Lower bounds: [x, y, width, height] for each plot
        xl = []
        xu = []
        
        min_dim = np.sqrt(min_plot_size)
        max_dim = np.sqrt(max_plot_size)
        
        for _ in range(n_plots):
            xl.extend([0, 0, min_dim, min_dim])  # Normalized x, y; dimensions in meters
            xu.extend([1, 1, max_dim, max_dim])
        
        super().__init__(
            n_var=n_var,
            n_obj=3,  # 3 objectives (not 5!)
            n_ieq_constr=n_constr,  # Inequality constraints (g <= 0 is violation)
            xl=np.array(xl),
            xu=np.array(xu),
            **kwargs
        )
        
        logger.info(f"IndustrialEstateConstrainedProblem: {n_plots} plots, {n_constr} constraints")
    
    def _evaluate(self, x, out, *args, **kwargs):
        """
        Evaluate population of solutions
        
        Args:
            x: Decision variables (N_individuals x n_var)
            out: Output dictionary with "F" (objectives) and "G" (constraints)
        """
        N = x.shape[0]
        
        # Decode to layouts
        layouts = self._decode_layouts(x)
        
        # Calculate objectives
        f1 = np.zeros(N)  # -Sellable area (maximize)
        f2 = np.zeros(N)  # -Green space potential (maximize)
        f3 = np.zeros(N)  # Road length estimate
        
        # Calculate constraints
        n_overlap = int(self.n_plots * (self.n_plots - 1) / 2)
        n_containment = self.n_plots
        g = np.zeros((N, n_overlap + n_containment))
        
        for i in range(N):
            layout = layouts[i]
            
            # === OBJECTIVES ===
            
            # F1: Maximize sellable area (negate for minimization)
            total_area = sum(p['width'] * p['height'] for p in layout)
            f1[i] = -total_area
            
            # F2: Maximize green space potential (based on plot arrangement)
            # Simplified: favor layouts with clustered plots (more contiguous green)
            if len(layout) > 1:
                centroids = [(p['x'], p['y']) for p in layout]
                avg_x = np.mean([c[0] for c in centroids])
                avg_y = np.mean([c[1] for c in centroids])
                spread = sum(np.sqrt((c[0]-avg_x)**2 + (c[1]-avg_y)**2) for c in centroids)
                f2[i] = spread  # Minimize spread = maximize clustering
            else:
                f2[i] = 0
            
            # F3: Estimate road length needed (based on centroid distances)
            if len(layout) > 1:
                total_dist = 0
                for j, p1 in enumerate(layout):
                    for p2 in layout[j+1:]:
                        dx = p1['x'] - p2['x']
                        dy = p1['y'] - p2['y']
                        total_dist += np.sqrt(dx**2 + dy**2)
                f3[i] = total_dist
            else:
                f3[i] = 0
            
            # === CONSTRAINTS ===
            # Hard constraints: g <= 0 means violation, g > 0 means satisfied
            
            g_idx = 0
            
            # G1: No overlaps (separation constraint)
            for j, p1 in enumerate(layout):
                for k in range(j+1, len(layout)):
                    p2 = layout[k]
                    
                    # Calculate minimum distance between plot edges
                    dx = abs(p1['x'] - p2['x'])
                    dy = abs(p1['y'] - p2['y'])
                    
                    # Half-widths
                    hw1 = p1['width'] / 2
                    hw2 = p2['width'] / 2
                    hh1 = p1['height'] / 2
                    hh2 = p2['height'] / 2
                    
                    # Separation in x and y
                    sep_x = dx - hw1 - hw2
                    sep_y = dy - hh1 - hh2
                    
                    # Constraint: min(sep_x, sep_y) >= min_separation
                    # Reformulated: min_separation - max(sep_x, sep_y) <= 0
                    # If sep_x > 0 OR sep_y > 0, plots don't overlap
                    max_sep = max(sep_x, sep_y)
                    g[i, g_idx] = self.min_separation - max_sep  # <= 0 means OK
                    g_idx += 1
            
            # G2: Containment (all plots within buildable area)
            for j, p in enumerate(layout):
                plot_geom = self._create_plot_geometry(p)
                if self.buildable_area.contains(plot_geom):
                    g[i, g_idx] = -1  # Satisfied (< 0)
                else:
                    # How much outside?
                    outside_area = plot_geom.difference(self.buildable_area).area
                    g[i, g_idx] = outside_area  # Violation (> 0)
                g_idx += 1
        
        # Set outputs
        out["F"] = np.column_stack([f1, f2, f3])
        out["G"] = g
    
    def _decode_layouts(self, x: np.ndarray) -> List[List[Dict]]:
        """
        Decode decision variables to layout representations
        
        Args:
            x: Decision variables (N x n_var)
            
        Returns:
            List of layouts, each layout is a list of plot dicts
        """
        minx, miny, maxx, maxy = self.bounds
        width_range = maxx - minx
        height_range = maxy - miny
        
        layouts = []
        for i in range(x.shape[0]):
            layout = []
            for j in range(self.n_plots):
                idx = j * 4
                
                # Decode position (normalized to actual coordinates)
                px = minx + x[i, idx] * width_range
                py = miny + x[i, idx + 1] * height_range
                
                # Dimensions are already in meters
                width = x[i, idx + 2]
                height = x[i, idx + 3]
                
                layout.append({
                    'id': j,
                    'x': px,
                    'y': py,
                    'width': width,
                    'height': height,
                    'area': width * height
                })
            
            layouts.append(layout)
        
        return layouts
    
    def _create_plot_geometry(self, plot: Dict) -> Polygon:
        """Create Shapely polygon from plot dict"""
        x, y = plot['x'], plot['y']
        w, h = plot['width'], plot['height']
        
        # Center-based
        return box(x - w/2, y - h/2, x + w/2, y + h/2)


def solve_constrained_layout(
    site_boundary: Polygon,
    buildable_area: Polygon,
    n_plots: int = 10,
    population_size: int = 100,
    n_generations: int = 100,
    min_plot_size: float = 900,
    max_plot_size: float = 10000,
    seed: int = None,
    verbose: bool = False
) -> Dict:
    """
    Solve industrial estate layout using NSGA-II with hard constraints
    
    Args:
        site_boundary: Overall site polygon
        buildable_area: Buildable area (after setbacks)
        n_plots: Number of plots to place
        population_size: GA population size
        n_generations: Number of generations
        min_plot_size: Minimum plot area (m²)
        max_plot_size: Maximum plot area (m²)
        seed: Random seed
        verbose: Print progress
        
    Returns:
        Result dict with Pareto-optimal solutions
    """
    logger.info(f"Starting constrained NSGA-II optimization")
    logger.info(f"  Plots: {n_plots}, Pop: {population_size}, Gen: {n_generations}")
    
    # Create problem
    problem = IndustrialEstateConstrainedProblem(
        site_boundary=site_boundary,
        buildable_area=buildable_area,
        n_plots=n_plots,
        min_plot_size=min_plot_size,
        max_plot_size=max_plot_size
    )
    
    # Create NSGA-II algorithm
    algorithm = NSGA2(
        pop_size=population_size,
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(eta=20),
        eliminate_duplicates=True
    )
    
    # Run optimization
    result = minimize(
        problem,
        algorithm,
        ('n_gen', n_generations),
        seed=seed,
        verbose=verbose,
        save_history=False
    )
    
    # Process results
    if result.F is None or len(result.F) == 0:
        logger.warning("No feasible solutions found!")
        return {
            'success': False,
            'message': 'No feasible solutions found - constraints too tight',
            'n_solutions': 0,
            'layouts': []
        }
    
    # Get feasible solutions (constraint violations <= 0)
    feasible_mask = np.all(result.CV <= 0, axis=1) if result.CV is not None else np.ones(len(result.F), dtype=bool)
    n_feasible = np.sum(feasible_mask)
    
    logger.info(f"✅ Optimization complete!")
    logger.info(f"   Total solutions: {len(result.F)}")
    logger.info(f"   Feasible solutions: {n_feasible}")
    
    if n_feasible > 0:
        logger.info(f"   Objectives range:")
        logger.info(f"   - Sellable Area: {-result.F[feasible_mask, 0].max():.0f} - {-result.F[feasible_mask, 0].min():.0f} m²")
        logger.info(f"   - Clustering: {result.F[feasible_mask, 1].min():.1f} - {result.F[feasible_mask, 1].max():.1f}")
        logger.info(f"   - Road Length: {result.F[feasible_mask, 2].min():.1f} - {result.F[feasible_mask, 2].max():.1f}")
    
    # Convert to layouts
    layouts = problem._decode_layouts(result.X)
    
    return {
        'success': True,
        'n_solutions': len(result.F),
        'n_feasible': n_feasible,
        'objectives': result.F.tolist(),
        'constraint_violations': result.CV.tolist() if result.CV is not None else None,
        'layouts': layouts,
        'pareto_front': result.F[feasible_mask].tolist() if n_feasible > 0 else []
    }


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create sample site
    site = box(0, 0, 500, 400)
    buildable = site.buffer(-50)  # 50m setback
    
    # Run optimization
    result = solve_constrained_layout(
        site_boundary=site,
        buildable_area=buildable,
        n_plots=6,
        population_size=50,
        n_generations=50,
        seed=42,
        verbose=True
    )
    
    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"Success: {result['success']}")
    print(f"Pareto solutions: {result['n_solutions']}")
    print(f"Feasible: {result['n_feasible']}")
    
    if result['layouts']:
        best_layout = result['layouts'][0]
        print(f"\nBest layout ({len(best_layout)} plots):")
        for p in best_layout[:3]:
            print(f"  Plot {p['id']}: ({p['x']:.1f}, {p['y']:.1f}) - {p['area']:.0f} m²")
