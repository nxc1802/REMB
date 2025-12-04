"""
NSGA-II Optimizer - Module A: The Architect
Multi-objective genetic algorithm for industrial estate layout optimization
"""
import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.optimize import minimize
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from typing import List, Tuple
import yaml
from pathlib import Path

from src.models.domain import Layout, SiteBoundary, Plot, PlotType, ParetoFront, RoadNetwork
from shapely.geometry import Polygon, box
import logging

logger = logging.getLogger(__name__)


class IndustrialEstateProblem(Problem):
    """
    Multi-objective optimization problem for industrial estate layout
    
    Objectives:
    1. Maximize sellable area
    2. Maximize green space
    3. Minimize road network length
    4. Maximize regulatory compliance score
    """
    
    def __init__(self, site_boundary: SiteBoundary, regulations: dict, n_plots: int = 20):
        """
        Initialize optimization problem
        
        Args:
            site_boundary: Site boundary with constraints
            regulations: Regulatory requirements from YAML
            n_plots: Target number of industrial plots
        """
        self.site_boundary = site_boundary
        self.regulations = regulations
        self.n_plots = n_plots
        
        # Decision variables: [x1, y1, width1, height1, orientation1, ..., xN, yN, widthN, heightN, orientationN]
        # 5 variables per plot: x, y position (normalized), width, height (meters), orientation (0-360)
        n_var = n_plots * 5
        
        # Variable bounds
        xl = np.array([0, 0, 20, 20, 0] * n_plots)  # Lower bounds
        xu = np.array([1, 1, 200, 200, 360] * n_plots)  # Upper bounds
        
        super().__init__(
            n_var=n_var,
            n_obj=4,  # 4 objectives
            n_constr=0,  # Constraints handled via penalties
            xl=xl,
            xu=xu
        )
    
    def _evaluate(self, X, out, *args, **kwargs):
        """
        Evaluate population
        
        Args:
            X: Population matrix (n_individuals x n_variables)
            out: Output dictionary
        """
        n_individuals = X.shape[0]
        
        # Initialize objective arrays
        f1_sellable = np.zeros(n_individuals)  # Maximize (will negate)
        f2_green = np.zeros(n_individuals)  # Maximize (will negate)
        f3_road_length = np.zeros(n_individuals)  # Minimize
        f4_compliance = np.zeros(n_individuals)  # Maximize (will negate)
        
        for i in range(n_individuals):
            layout = self._decode_solution(X[i])
            
            # Calculate objectives
            metrics = layout.calculate_metrics()
            
            # F1: Maximize sellable area (negate for minimization)
            f1_sellable[i] = -metrics.sellable_area_sqm
            
            # F2: Maximize green space (negate for minimization)
            f2_green[i] = -metrics.green_space_area_sqm
            
            # F3: Minimize road network length
            if layout.road_network:
                f3_road_length[i] = layout.road_network.total_length_m
            else:
                f3_road_length[i] = 1e6  # Penalty for no road
            
            # F4: Regulatory compliance score (0-1, higher is better)
            compliance_score = self._calculate_compliance_score(layout)
            f4_compliance[i] = -compliance_score  # Negate for minimization
        
        # Set objectives
        out["F"] = np.column_stack([f1_sellable, f2_green, f3_road_length, f4_compliance])
    
    def _decode_solution(self, x: np.ndarray) -> Layout:
        """
        Decode decision variables into a Layout
        
        Args:
            x: Decision variables array
            
        Returns:
            Layout object
        """
        layout = Layout(site_boundary=self.site_boundary)
        
        # Get site bounds for denormalization
        minx, miny, maxx, maxy = self.site_boundary.geometry.bounds
        site_width = maxx - minx
        site_height = maxy - miny
        
        plots = []
        for i in range(self.n_plots):
            idx = i * 5
            
            # Denormalize position
            x_norm, y_norm = x[idx], x[idx + 1]
            x_pos = minx + x_norm * site_width
            y_pos = miny + y_norm * site_height
            
            width, height = x[idx + 2], x[idx + 3]
            orientation = x[idx + 4]
            
            # Create simple rectangular plot
            plot_geom = box(x_pos, y_pos, x_pos + width, y_pos + height)
            
            # Check if plot is within buildable area
            if not self.site_boundary.geometry.contains(plot_geom):
                continue  # Skip invalid plots
            
            plot = Plot(
                geometry=plot_geom,
                area_sqm=plot_geom.area,
                type=PlotType.INDUSTRIAL,
                width_m=width,
                depth_m=height,
                orientation_degrees=orientation
            )
            plots.append(plot)
        
        # Add green space (simplified: use remaining area)
        # In practice, this would be more sophisticated
        green_area_target = self.site_boundary.buildable_area_sqm * 0.15  # 15% minimum
        
        layout.plots = plots
        layout.road_network = RoadNetwork()  # Simplified
        
        return layout
    
    def _calculate_compliance_score(self, layout: Layout) -> float:
        """
        Calculate regulatory compliance score (0-1)
        
        Args:
            layout: Layout to evaluate
            
        Returns:
            Compliance score (1.0 = fully compliant)
        """
        score = 1.0
        penalties = 0
        
        metrics = layout.metrics
        
        # Check green space requirement
        min_green = self.regulations.get('green_space', {}).get('minimum_percentage', 0.15)
        if metrics.green_space_ratio < min_green:
            penalties += 0.3
        
        # Check FAR
        max_far = self.regulations.get('far', {}).get('maximum', 0.7)
        if metrics.far_value > max_far:
            penalties += 0.3
        
        # Check plot sizes
        min_plot_size = self.regulations.get('plot', {}).get('minimum_area_sqm', 1000)
        for plot in layout.plots:
            if plot.type == PlotType.INDUSTRIAL and plot.area_sqm < min_plot_size:
                penalties += 0.1
                break
        
        score = max(0.0, score - penalties)
        return score


class NSGA2Optimizer:
    """
    NSGA-II based multi-objective optimizer for industrial estate layouts
    """
    
    def __init__(self, config_path: str = "config/regulations.yaml"):
        """
        Initialize optimizer
        
        Args:
            config_path: Path to regulations YAML file
        """
        self.config_path = Path(config_path)
        self.regulations = self._load_regulations()
        self.logger = logging.getLogger(__name__)
    
    def _load_regulations(self) -> dict:
        """Load regulations from YAML file"""
        if not self.config_path.exists():
            self.logger.warning(f"Regulations file not found: {self.config_path}")
            return {}
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def optimize(
        self,
        site_boundary: SiteBoundary,
        population_size: int = 100,
        n_generations: int = 200,
        n_plots: int = 20
    ) -> ParetoFront:
        """
        Run NSGA-II optimization
        
        Args:
            site_boundary: Site boundary with constraints
            population_size: NSGA-II population size
            n_generations: Number of generations
            n_plots: Target number of plots
            
        Returns:
            ParetoFront with optimal solutions
        """
        import time
        start_time = time.time()
        
        self.logger.info(f"Starting NSGA-II optimization: pop={population_size}, gen={n_generations}")
        
        # Define problem
        problem = IndustrialEstateProblem(
            site_boundary=site_boundary,
            regulations=self.regulations,
            n_plots=n_plots
        )
        
        # Define algorithm
        algorithm = NSGA2(
            pop_size=population_size,
            sampling=FloatRandomSampling(),
            crossover=SBX(prob=0.9, eta=15),
            mutation=PM(eta=20),
            eliminate_duplicates=True
        )
        
        # Run optimization
        result = minimize(
            problem,
            algorithm,
            ('n_gen', n_generations),
            seed=42,
            verbose=True
        )
        
        # Extract Pareto front
        pareto_front = ParetoFront()
        
        if result.X is not None:
            # result.X can be 1D or 2D depending on number of solutions
            if len(result.X.shape) == 1:
                solutions = [result.X]
            else:
                solutions = result.X
            
            for i, x in enumerate(solutions):
                layout = problem._decode_solution(x)
                layout.pareto_rank = i
                layout.calculate_metrics()
                
                # Store fitness scores
                if len(result.F.shape) == 1:
                    f = result.F
                else:
                    f = result.F[i]
                
                layout.fitness_scores = {
                    'sellable_area': -f[0],  # Negate back
                    'green_space': -f[1],
                    'road_length': f[2],
                    'compliance': -f[3]
                }
                
                pareto_front.layouts.append(layout)
        
        pareto_front.generation_time_seconds = time.time() - start_time
        
        self.logger.info(f"Optimization complete: {len(pareto_front.layouts)} solutions in {pareto_front.generation_time_seconds:.2f}s")
        
        return pareto_front


# Example usage
if __name__ == "__main__":
    # Example: Create a simple rectangular site
    from shapely.geometry import box
    
    site_geom = box(0, 0, 500, 500)  # 500m x 500m site
    site = SiteBoundary(
        geometry=site_geom,
        area_sqm=site_geom.area
    )
    site.buildable_area_sqm = site.area_sqm
    
    # Run optimization
    optimizer = NSGA2Optimizer()
    pareto_front = optimizer.optimize(
        site_boundary=site,
        population_size=50,
        n_generations=100,
        n_plots=15
    )
    
    print(f"Generated {len(pareto_front.layouts)} Pareto-optimal layouts")
    
    # Show best layouts
    max_sellable = pareto_front.get_max_sellable_layout()
    if max_sellable:
        print(f"Max sellable area: {max_sellable.metrics.sellable_area_sqm:.2f} m²")
    
    max_green = pareto_front.get_max_green_layout()
    if max_green:
        print(f"Max green space: {max_green.metrics.green_space_area_sqm:.2f} m²")
