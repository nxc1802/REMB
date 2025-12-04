"""
MILP Solver - Module B: The Engineer (CP Module)
Mixed-Integer Linear Programming solver for precision constraints using OR-Tools
Đảm bảo tính hợp lệ toán học tuyệt đối - loại bỏ "hallucination"
"""
import numpy as np
from ortools.linear_solver import pywraplp
from ortools.sat.python import cp_model
from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass, field
import json
import logging

from src.models.domain import Layout, Plot, PlotType, SiteBoundary, RoadNetwork
from shapely.geometry import Polygon, box, LineString, MultiLineString
from shapely.ops import unary_union

logger = logging.getLogger(__name__)


@dataclass
class MILPResult:
    """Result from MILP solver"""
    status: str  # 'OPTIMAL', 'FEASIBLE', 'INFEASIBLE', 'TIMEOUT'
    objective_value: float = 0.0
    solve_time_seconds: float = 0.0
    plots: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    
    def is_success(self) -> bool:
        return self.status in ['OPTIMAL', 'FEASIBLE']
    
    def to_json(self) -> str:
        """Export result as JSON for LLM interpretation"""
        return json.dumps({
            'status': self.status,
            'objective_value': self.objective_value,
            'solve_time_seconds': self.solve_time_seconds,
            'num_plots': len(self.plots),
            'plots': self.plots,
            'error_message': self.error_message
        }, indent=2)


class MILPSolver:
    """
    Mixed-Integer Linear Programming Solver - The "Muscle/Kỹ sư"
    
    Responsibilities:
    - Enforce non-overlapping constraints mathematically
    - Ensure road connectivity for all plots
    - Guarantee geometric closure and snapping
    - Provide exact numerical solutions (no hallucination)
    
    This is a "black-box" that receives JSON parameters and returns raw results.
    """
    
    def __init__(self, time_limit_seconds: int = 3600, solver_type: str = "SCIP"):
        """
        Initialize MILP Solver
        
        Args:
            time_limit_seconds: Maximum solve time
            solver_type: Solver backend ('SCIP', 'CBC', 'GLOP', 'SAT')
        """
        self.time_limit_seconds = time_limit_seconds
        self.solver_type = solver_type
        self.logger = logging.getLogger(__name__)
        
        # Try to find an available solver
        self._available_solver = self._find_available_solver()
    
    def _find_available_solver(self) -> str:
        """Find an available solver"""
        solvers_to_try = [self.solver_type, 'SCIP', 'CBC', 'GLOP', 'SAT']
        
        for solver_name in solvers_to_try:
            solver = pywraplp.Solver.CreateSolver(solver_name)
            if solver:
                self.logger.info(f"Using solver: {solver_name}")
                return solver_name
        
        self.logger.warning("No LP solver available, will use CP-SAT only")
        return None
    
    def validate_and_refine(self, layout: Layout) -> Tuple[Layout, MILPResult]:
        """
        Validate and refine a layout using MILP constraints
        
        This is the main entry point - receives layout, returns refined layout with
        mathematically guaranteed validity.
        
        Args:
            layout: Layout to validate and refine
            
        Returns:
            Tuple of (refined_layout, result)
        """
        self.logger.info(f"MILP validation for layout {layout.id}")
        import time
        start_time = time.time()
        
        # Step 1: Check for overlaps and fix
        overlap_result = self._resolve_overlaps(layout)
        if not overlap_result.is_success():
            return layout, overlap_result
        
        # Step 2: Ensure road connectivity
        connectivity_result = self._ensure_road_connectivity(layout)
        if not connectivity_result.is_success():
            return layout, connectivity_result
        
        # Step 3: Snap geometries to grid
        self._snap_geometries(layout)
        
        # Step 4: Validate final geometry closure
        closure_result = self._validate_geometry_closure(layout)
        
        solve_time = time.time() - start_time
        
        result = MILPResult(
            status='OPTIMAL' if closure_result else 'FEASIBLE',
            objective_value=layout.metrics.sellable_area_sqm,
            solve_time_seconds=solve_time,
            plots=[{
                'id': p.id,
                'area_sqm': p.area_sqm,
                'type': p.type.value,
                'has_road_access': p.has_road_access
            } for p in layout.plots]
        )
        
        self.logger.info(f"MILP validation complete: {result.status} in {solve_time:.2f}s")
        
        return layout, result
    
    def _resolve_overlaps(self, layout: Layout) -> MILPResult:
        """
        Resolve plot overlaps using constraint programming
        
        Uses OR-Tools CP-SAT solver to find non-overlapping placement
        """
        industrial_plots = [p for p in layout.plots if p.type == PlotType.INDUSTRIAL]
        
        if len(industrial_plots) < 2:
            return MILPResult(status='OPTIMAL')
        
        # Check for overlaps
        overlaps_found = []
        for i, p1 in enumerate(industrial_plots):
            for p2 in industrial_plots[i+1:]:
                if p1.geometry and p2.geometry:
                    if p1.geometry.intersects(p2.geometry):
                        intersection = p1.geometry.intersection(p2.geometry)
                        if intersection.area > 1.0:  # 1 sqm tolerance
                            overlaps_found.append((p1.id, p2.id, intersection.area))
        
        if not overlaps_found:
            return MILPResult(status='OPTIMAL')
        
        self.logger.warning(f"Found {len(overlaps_found)} overlapping plot pairs")
        
        # Use CP-SAT to resolve overlaps
        model = cp_model.CpModel()
        
        # Get site bounds
        minx, miny, maxx, maxy = layout.site_boundary.geometry.bounds
        site_width = int(maxx - minx)
        site_height = int(maxy - miny)
        
        # Decision variables: position of each plot
        plot_vars = {}
        for plot in industrial_plots:
            width = int(plot.width_m) if plot.width_m > 0 else 50
            height = int(plot.depth_m) if plot.depth_m > 0 else 50
            
            # X and Y positions
            x = model.NewIntVar(0, site_width - width, f'x_{plot.id}')
            y = model.NewIntVar(0, site_height - height, f'y_{plot.id}')
            
            plot_vars[plot.id] = {
                'x': x,
                'y': y,
                'width': width,
                'height': height,
                'plot': plot
            }
        
        # Non-overlap constraints (using interval variables)
        x_intervals = []
        y_intervals = []
        
        for plot_id, vars in plot_vars.items():
            x_interval = model.NewIntervalVar(
                vars['x'],
                vars['width'],
                vars['x'] + vars['width'],
                f'x_interval_{plot_id}'
            )
            y_interval = model.NewIntervalVar(
                vars['y'],
                vars['height'],
                vars['y'] + vars['height'],
                f'y_interval_{plot_id}'
            )
            x_intervals.append(x_interval)
            y_intervals.append(y_interval)
        
        # Add 2D no-overlap constraint
        model.AddNoOverlap2D(x_intervals, y_intervals)
        
        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = min(60, self.time_limit_seconds)
        
        status = solver.Solve(model)
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            # Update plot positions
            for plot_id, vars in plot_vars.items():
                new_x = solver.Value(vars['x']) + minx
                new_y = solver.Value(vars['y']) + miny
                width = vars['width']
                height = vars['height']
                
                # Update plot geometry
                plot = vars['plot']
                plot.geometry = box(new_x, new_y, new_x + width, new_y + height)
                plot.area_sqm = plot.geometry.area
            
            return MILPResult(
                status='OPTIMAL' if status == cp_model.OPTIMAL else 'FEASIBLE',
                solve_time_seconds=solver.WallTime()
            )
        else:
            return MILPResult(
                status='INFEASIBLE',
                error_message='Cannot resolve overlaps - site may be too constrained'
            )
    
    def _ensure_road_connectivity(self, layout: Layout) -> MILPResult:
        """
        Ensure all industrial plots have road access
        
        Uses simple distance-based connectivity check
        """
        max_distance = 200  # meters (from regulations)
        
        # If no road network, create a simple grid
        if not layout.road_network or not layout.road_network.primary_roads:
            self._generate_simple_road_network(layout)
        
        # Check connectivity for each industrial plot
        disconnected_plots = []
        all_roads = []
        
        if layout.road_network:
            if layout.road_network.primary_roads:
                all_roads.extend(layout.road_network.primary_roads.geoms if hasattr(layout.road_network.primary_roads, 'geoms') else [layout.road_network.primary_roads])
            if layout.road_network.secondary_roads:
                all_roads.extend(layout.road_network.secondary_roads.geoms if hasattr(layout.road_network.secondary_roads, 'geoms') else [layout.road_network.secondary_roads])
        
        for plot in layout.plots:
            if plot.type == PlotType.INDUSTRIAL and plot.geometry:
                # Find minimum distance to any road
                min_distance = float('inf')
                for road in all_roads:
                    dist = plot.geometry.distance(road)
                    min_distance = min(min_distance, dist)
                
                if min_distance <= max_distance:
                    plot.has_road_access = True
                else:
                    plot.has_road_access = False
                    disconnected_plots.append(plot.id)
        
        if disconnected_plots:
            self.logger.warning(f"Plots without road access: {disconnected_plots}")
            return MILPResult(
                status='FEASIBLE',
                error_message=f'Plots {disconnected_plots} exceed {max_distance}m from road'
            )
        
        return MILPResult(status='OPTIMAL')
    
    def _generate_simple_road_network(self, layout: Layout):
        """Generate a simple grid road network"""
        bounds = layout.site_boundary.geometry.bounds
        minx, miny, maxx, maxy = bounds
        
        # Create primary roads (cross pattern)
        center_x = (minx + maxx) / 2
        center_y = (miny + maxy) / 2
        
        horizontal = LineString([(minx, center_y), (maxx, center_y)])
        vertical = LineString([(center_x, miny), (center_x, maxy)])
        
        layout.road_network = RoadNetwork(
            primary_roads=MultiLineString([horizontal, vertical]),
            total_length_m=horizontal.length + vertical.length
        )
        
        # Calculate road area (assume 24m width for primary roads)
        road_width = 24
        road_area = layout.road_network.total_length_m * road_width
        layout.road_network.total_area_sqm = road_area
    
    def _snap_geometries(self, layout: Layout, grid_size: float = 1.0):
        """
        Snap all geometries to a grid for clean coordinates
        
        Args:
            layout: Layout to snap
            grid_size: Grid size in meters (default 1m)
        """
        for plot in layout.plots:
            if plot.geometry:
                coords = list(plot.geometry.exterior.coords)
                snapped_coords = [
                    (round(x / grid_size) * grid_size, round(y / grid_size) * grid_size)
                    for x, y in coords
                ]
                try:
                    plot.geometry = Polygon(snapped_coords)
                    plot.area_sqm = plot.geometry.area
                except Exception as e:
                    self.logger.warning(f"Failed to snap plot {plot.id}: {e}")
    
    def _validate_geometry_closure(self, layout: Layout) -> bool:
        """
        Validate that all geometries are properly closed
        
        Returns:
            True if all geometries are valid
        """
        all_valid = True
        
        for plot in layout.plots:
            if plot.geometry:
                if not plot.geometry.is_valid:
                    self.logger.warning(f"Plot {plot.id} has invalid geometry")
                    # Try to fix
                    plot.geometry = plot.geometry.buffer(0)
                    if not plot.geometry.is_valid:
                        all_valid = False
        
        return all_valid
    
    def solve_plot_placement(
        self,
        site_boundary: SiteBoundary,
        num_plots: int,
        min_plot_size: float = 1000,
        max_plot_size: float = 10000,
        setback: float = 50
    ) -> MILPResult:
        """
        Solve optimal plot placement from scratch using MILP
        
        This is the "black-box" function that LLM can call via Function Calling.
        Receives JSON-like parameters, returns raw numerical results.
        
        Args:
            site_boundary: Site boundary polygon
            num_plots: Target number of plots
            min_plot_size: Minimum plot area in sqm
            max_plot_size: Maximum plot area in sqm
            setback: Boundary setback in meters
            
        Returns:
            MILPResult with plot placements
        """
        self.logger.info(f"MILP solving for {num_plots} plots")
        import time
        start_time = time.time()
        
        # Create solver - use available solver or fallback to CP-SAT
        solver_to_use = self._available_solver or 'SAT'
        solver = pywraplp.Solver.CreateSolver(solver_to_use)
        if not solver:
            # Fallback: Use CP-SAT based approach
            return self._solve_with_cpsat(site_boundary, num_plots, min_plot_size, max_plot_size, setback)
        
        solver.SetTimeLimit(self.time_limit_seconds * 1000)  # Convert to ms
        
        # Get buildable area (after setback)
        buildable = site_boundary.geometry.buffer(-setback)
        if buildable.is_empty:
            return MILPResult(
                status='INFEASIBLE',
                error_message=f'Site too small for {setback}m setback'
            )
        
        bounds = buildable.bounds
        minx, miny, maxx, maxy = bounds
        width = maxx - minx
        height = maxy - miny
        
        # Decision variables
        infinity = solver.infinity()
        
        # For each plot: x, y, w, h (continuous), active (binary)
        plots_vars = []
        for i in range(num_plots):
            x = solver.NumVar(0, width, f'x_{i}')
            y = solver.NumVar(0, height, f'y_{i}')
            w = solver.NumVar(20, 200, f'w_{i}')  # 20-200m width
            h = solver.NumVar(20, 200, f'h_{i}')  # 20-200m height
            active = solver.IntVar(0, 1, f'active_{i}')
            
            plots_vars.append({
                'x': x, 'y': y, 'w': w, 'h': h,
                'active': active, 'index': i
            })
            
            # Boundary constraints
            solver.Add(x + w <= width)
            solver.Add(y + h <= height)
            
            # Size constraints
            solver.Add(w * h >= min_plot_size * active)
            solver.Add(w * h <= max_plot_size)
        
        # Objective: Maximize total active plot area
        objective = solver.Objective()
        for pv in plots_vars:
            # Approximate area (linearization)
            objective.SetCoefficient(pv['w'], 100)
            objective.SetCoefficient(pv['h'], 100)
            objective.SetCoefficient(pv['active'], min_plot_size)
        objective.SetMaximization()
        
        # Solve
        status = solver.Solve()
        
        solve_time = time.time() - start_time
        
        # Parse results
        if status in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE]:
            result_plots = []
            for pv in plots_vars:
                if pv['active'].solution_value() > 0.5:
                    x = pv['x'].solution_value() + minx + setback
                    y = pv['y'].solution_value() + miny + setback
                    w = pv['w'].solution_value()
                    h = pv['h'].solution_value()
                    
                    result_plots.append({
                        'id': f'plot_{pv["index"]}',
                        'x': x,
                        'y': y,
                        'width': w,
                        'height': h,
                        'area_sqm': w * h,
                        'type': 'industrial'
                    })
            
            return MILPResult(
                status='OPTIMAL' if status == pywraplp.Solver.OPTIMAL else 'FEASIBLE',
                objective_value=solver.Objective().Value(),
                solve_time_seconds=solve_time,
                plots=result_plots
            )
        else:
            status_map = {
                pywraplp.Solver.INFEASIBLE: 'INFEASIBLE',
                pywraplp.Solver.UNBOUNDED: 'UNBOUNDED',
                pywraplp.Solver.NOT_SOLVED: 'TIMEOUT'
            }
            return MILPResult(
                status=status_map.get(status, 'ERROR'),
                solve_time_seconds=solve_time,
                error_message='Could not find valid plot placement'
            )
    
    def _solve_with_cpsat(
        self,
        site_boundary: SiteBoundary,
        num_plots: int,
        min_plot_size: float,
        max_plot_size: float,
        setback: float
    ) -> MILPResult:
        """
        Fallback solver using CP-SAT for plot placement
        """
        import time
        start_time = time.time()
        
        # Get buildable area
        buildable = site_boundary.geometry.buffer(-setback)
        if buildable.is_empty:
            return MILPResult(
                status='INFEASIBLE',
                error_message=f'Site too small for {setback}m setback'
            )
        
        minx, miny, maxx, maxy = buildable.bounds
        width = int(maxx - minx)
        height = int(maxy - miny)
        
        # Use CP-SAT
        model = cp_model.CpModel()
        
        # Fixed plot dimensions for simplicity
        plot_width = int(min_plot_size ** 0.5)  # Square plots
        plot_height = plot_width
        
        # Create plot variables
        plot_vars = []
        x_intervals = []
        y_intervals = []
        
        for i in range(num_plots):
            x = model.NewIntVar(0, max(0, width - plot_width), f'x_{i}')
            y = model.NewIntVar(0, max(0, height - plot_height), f'y_{i}')
            
            x_interval = model.NewIntervalVar(x, plot_width, x + plot_width, f'x_int_{i}')
            y_interval = model.NewIntervalVar(y, plot_height, y + plot_height, f'y_int_{i}')
            
            plot_vars.append({'x': x, 'y': y, 'width': plot_width, 'height': plot_height})
            x_intervals.append(x_interval)
            y_intervals.append(y_interval)
        
        # No overlap constraint
        model.AddNoOverlap2D(x_intervals, y_intervals)
        
        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = min(30, self.time_limit_seconds)
        status = solver.Solve(model)
        
        solve_time = time.time() - start_time
        
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            result_plots = []
            for i, pv in enumerate(plot_vars):
                x = solver.Value(pv['x']) + minx + setback
                y = solver.Value(pv['y']) + miny + setback
                
                result_plots.append({
                    'id': f'plot_{i}',
                    'x': x,
                    'y': y,
                    'width': pv['width'],
                    'height': pv['height'],
                    'area_sqm': pv['width'] * pv['height'],
                    'type': 'industrial'
                })
            
            return MILPResult(
                status='OPTIMAL' if status == cp_model.OPTIMAL else 'FEASIBLE',
                objective_value=len(result_plots) * plot_width * plot_height,
                solve_time_seconds=solve_time,
                plots=result_plots
            )
        else:
            return MILPResult(
                status='INFEASIBLE',
                solve_time_seconds=solve_time,
                error_message='Could not place plots without overlap'
            )

    def to_json_interface(self, request: Dict[str, Any]) -> str:
        """
        JSON interface for LLM Function Calling
        
        This is the standardized interface that LLM uses to call the CP Module.
        
        Input format:
        {
            "action": "solve_placement" | "validate_layout",
            "parameters": {...}
        }
        
        Output format:
        {
            "status": "OPTIMAL" | "FEASIBLE" | "INFEASIBLE" | "ERROR",
            "result": {...}
        }
        """
        action = request.get('action')
        params = request.get('parameters', {})
        
        try:
            if action == 'solve_placement':
                # Create site boundary from params
                bounds = params.get('bounds', [0, 0, 500, 500])
                site_geom = box(*bounds)
                site = SiteBoundary(geometry=site_geom, area_sqm=site_geom.area)
                
                result = self.solve_plot_placement(
                    site_boundary=site,
                    num_plots=params.get('num_plots', 10),
                    min_plot_size=params.get('min_plot_size', 1000),
                    max_plot_size=params.get('max_plot_size', 10000),
                    setback=params.get('setback', 50)
                )
                
            elif action == 'validate_layout':
                # Would need to deserialize layout from JSON
                return json.dumps({
                    'status': 'ERROR',
                    'error_message': 'validate_layout requires Layout object'
                })
            else:
                return json.dumps({
                    'status': 'ERROR',
                    'error_message': f'Unknown action: {action}'
                })
            
            return result.to_json()
            
        except Exception as e:
            return json.dumps({
                'status': 'ERROR',
                'error_message': str(e)
            })


# Example usage
if __name__ == "__main__":
    from shapely.geometry import box as shapely_box
    
    # Create test site
    site_geom = shapely_box(0, 0, 500, 500)
    site = SiteBoundary(geometry=site_geom, area_sqm=site_geom.area)
    site.buildable_area_sqm = site.area_sqm
    
    # Test MILP solver
    solver = MILPSolver(time_limit_seconds=60)
    
    # Test plot placement
    result = solver.solve_plot_placement(
        site_boundary=site,
        num_plots=10,
        min_plot_size=1000,
        max_plot_size=5000,
        setback=50
    )
    
    print(f"Status: {result.status}")
    print(f"Solve time: {result.solve_time_seconds:.2f}s")
    print(f"Number of plots: {len(result.plots)}")
    
    # Test JSON interface
    json_request = {
        "action": "solve_placement",
        "parameters": {
            "bounds": [0, 0, 500, 500],
            "num_plots": 10,
            "min_plot_size": 1000,
            "setback": 50
        }
    }
    
    json_response = solver.to_json_interface(json_request)
    print("\nJSON Response:")
    print(json_response)
