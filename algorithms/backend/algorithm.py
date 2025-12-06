"""Core land redistribution algorithm implementation.

This module contains the exact algorithm logic from algo.ipynb for:
- Stage 1: Grid optimization using NSGA-II genetic algorithm
- Stage 2: Block subdivision using OR-Tools
- Stage 3: Infrastructure planning
"""

import random
import numpy as np
from typing import List, Tuple, Dict, Any
from shapely.geometry import Polygon, Point, LineString, MultiPolygon
from shapely.affinity import translate, rotate
from deap import base, creator, tools, algorithms
from ortools.sat.python import cp_model


class GridOptimizer:
    """Stage 1: Optimize grid layout using NSGA-II genetic algorithm."""
    
    def __init__(self, land_polygon: Polygon, lake_polygon: Polygon = None):
        """
        Initialize grid optimizer.
        
        Args:
            land_polygon: Main land boundary
            lake_polygon: Water body to exclude (optional)
        """
        self.land_poly = land_polygon
        self.lake_poly = lake_polygon or Polygon()
        
        # Setup DEAP genetic algorithm
        self._setup_deap()
    
    def _setup_deap(self):
        """Configure DEAP toolbox for multi-objective optimization."""
        # Create fitness and individual classes
        if not hasattr(creator, "FitnessMulti"):
            creator.create("FitnessMulti", base.Fitness, weights=(1.0, -1.0))  # Max area, Min fragments
        if not hasattr(creator, "Individual"):
            creator.create("Individual", list, fitness=creator.FitnessMulti)
        
        self.toolbox = base.Toolbox()
        # Gene 1: Block spacing (20m - 40m)
        self.toolbox.register("attr_spacing", random.uniform, 20, 40)
        # Gene 2: Rotation angle (0 - 90 degrees)
        self.toolbox.register("attr_angle", random.uniform, 0, 90)
        
        self.toolbox.register("individual", tools.initCycle, creator.Individual,
                             (self.toolbox.attr_spacing, self.toolbox.attr_angle), n=1)
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        
        self.toolbox.register("evaluate", self._evaluate_layout)
        self.toolbox.register("mate", tools.cxSimulatedBinaryBounded, low=[20, 0], up=[40, 90], eta=20.0)
        self.toolbox.register("mutate", tools.mutPolynomialBounded, low=[20, 0], up=[40, 90], eta=20.0, indpb=0.2)
        self.toolbox.register("select", tools.selNSGA2)
    
    def generate_grid_candidates(self, spacing: float, angle_deg: float) -> List[Polygon]:
        """
        Generate grid blocks at given spacing and rotation.
        
        Args:
            spacing: Grid spacing in meters
            angle_deg: Rotation angle in degrees
            
        Returns:
            List of block polygons
        """
        minx, miny, maxx, maxy = self.land_poly.bounds
        diameter = ((maxx - minx)**2 + (maxy - miny)**2)**0.5
        center = self.land_poly.centroid
        
        # Create grid ranges
        x_range = np.arange(minx - diameter, maxx + diameter, spacing)
        y_range = np.arange(miny - diameter, maxy + diameter, spacing)
        
        blocks = []
        
        # Create base block at origin
        base_block = Polygon([(0, 0), (spacing, 0), (spacing, spacing), (0, spacing)])
        base_block = translate(base_block, -spacing/2, -spacing/2)
        
        for x in x_range:
            for y in y_range:
                # Translate and rotate block
                poly = translate(base_block, x, y)
                poly = rotate(poly, angle_deg, origin=center)
                
                # Only keep blocks that intersect land
                if poly.intersects(self.land_poly):
                    blocks.append(poly)
        
        return blocks
    
    def _evaluate_layout(self, individual: List[float]) -> Tuple[float, int]:
        """
        Evaluate layout fitness.
        
        Objectives:
        1. Maximize residential area
        2. Minimize fragmented blocks
        
        Args:
            individual: [spacing, angle]
            
        Returns:
            (total_residential_area, fragmented_blocks)
        """
        spacing, angle = individual
        blocks = self.generate_grid_candidates(spacing, angle)
        
        total_residential_area = 0
        fragmented_blocks = 0
        
        for blk in blocks:
            # Cut with land boundary
            intersection = blk.intersection(self.land_poly)
            if intersection.is_empty:
                continue
            
            # Subtract lake
            usable_part = intersection.difference(self.lake_poly)
            if usable_part.is_empty:
                continue
            
            # Calculate area ratio
            original_area = spacing * spacing
            actual_area = usable_part.area
            ratio = actual_area / original_area
            
            # Classify block quality
            if ratio > 0.65:
                # Good block for residential
                total_residential_area += actual_area
            elif ratio > 0.1:
                # Fragmented block (penalize)
                fragmented_blocks += 1
        
        return (total_residential_area, fragmented_blocks)
    
    def optimize(self, population_size: int = 30, generations: int = 15) -> Tuple[List[float], List[List[float]]]:
        """
        Run NSGA-II optimization.
        
        Args:
            population_size: Population size
            generations: Number of generations
            
        Returns:
            (best_solution, history)
        """
        random.seed(42)
        pop = self.toolbox.population(n=population_size)
        
        history = []
        
        # Initial evaluation
        fits = list(map(self.toolbox.evaluate, pop))
        for ind, fit in zip(pop, fits):
            ind.fitness.values = fit
        
        # Save best from generation 0
        best_ind = tools.selBest(pop, 1)[0]
        history.append(list(best_ind))
        
        # Evolution
        for gen in range(generations):
            offspring = algorithms.varAnd(pop, self.toolbox, cxpb=0.7, mutpb=0.3)
            fits = list(map(self.toolbox.evaluate, offspring))
            for ind, fit in zip(offspring, fits):
                ind.fitness.values = fit
            pop = self.toolbox.select(pop + offspring, k=len(pop))
            
            # Save best from each generation
            best_ind = tools.selBest(pop, 1)[0]
            history.append(list(best_ind))
        
        final_best = tools.selBest(pop, 1)[0]
        return list(final_best), history


class SubdivisionSolver:
    """Stage 2: Optimize block subdivision using OR-Tools."""
    
    @staticmethod
    def solve_subdivision(total_length: float, min_width: float, max_width: float, 
                         target_width: float, time_limit: int = 10) -> List[float]:
        """
        Solve optimal lot widths using constraint programming.
        
        Args:
            total_length: Total length to subdivide
            min_width: Minimum lot width
            max_width: Maximum lot width
            target_width: Target lot width
            time_limit: Solver time limit in seconds
            
        Returns:
            List of lot widths
        """
        model = cp_model.CpModel()
        
        # Estimate number of lots
        max_lots = int(total_length / min_width) + 1
        
        # Decision variables: lot widths (scaled to integers)
        scale = 100  # 1cm precision
        lot_vars = [model.NewIntVar(int(min_width * scale), int(max_width * scale), f'lot_{i}')
                    for i in range(max_lots)]
        
        # Used lot indicators
        used = [model.NewBoolVar(f'used_{i}') for i in range(max_lots)]
        
        # Constraints
        # Sum of widths must equal total length
        model.Add(sum(lot_vars[i] for i in range(max_lots)) == int(total_length * scale))
        
        # Lot ordering (if used, previous must be used)
        for i in range(1, max_lots):
            model.Add(used[i] <= used[i-1])
        
        # Connect lot values to usage
        for i in range(max_lots):
            model.Add(lot_vars[i] >= int(min_width * scale)).OnlyEnforceIf(used[i])
            model.Add(lot_vars[i] == 0).OnlyEnforceIf(used[i].Not())
        
        # Minimize deviation from target
        deviations = [model.NewIntVar(0, int((max_width - min_width) * scale), f'dev_{i}')
                     for i in range(max_lots)]
        
        target_scaled = int(target_width * scale)
        for i in range(max_lots):
            model.AddAbsEquality(deviations[i], lot_vars[i] - target_scaled)
        
        model.Minimize(sum(deviations))
        
        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit
        status = solver.Solve(model)
        
        # Extract solution
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            widths = []
            for i in range(max_lots):
                if solver.Value(used[i]):
                    widths.append(solver.Value(lot_vars[i]) / scale)
            return widths
        else:
            # Fallback: uniform division
            num_lots = int(total_length / target_width)
            return [total_length / num_lots] * num_lots
    
    @staticmethod
    def subdivide_block(block_geom: Polygon, spacing: float, min_width: float, 
                       max_width: float, target_width: float, time_limit: int = 5) -> Dict[str, Any]:
        """
        Subdivide a block into lots.
        
        Args:
            block_geom: Block geometry
            spacing: Grid spacing
            min_width: Minimum lot width
            max_width: Maximum lot width
            target_width: Target lot width
            
        Returns:
            Dictionary with subdivision info
        """
        # Determine block quality
        original_area = spacing * spacing
        current_area = block_geom.area
        ratio = current_area / original_area
        
        result = {
            'geometry': block_geom,
            'type': 'unknown',
            'lots': []
        }
        
        # Fragmented blocks become parks
        if ratio < 0.6:
            result['type'] = 'park'
            return result
        
        # Good blocks become residential
        result['type'] = 'residential'
        
        # Solve subdivision
        minx, miny, maxx, maxy = block_geom.bounds
        total_width = maxx - minx
        
        lot_widths = SubdivisionSolver.solve_subdivision(
            total_width, min_width, max_width, target_width, time_limit
        )
        
        # Create lot geometries (simplified)
        current_x = minx
        for width in lot_widths:
            lot_poly = Polygon([
                (current_x, miny),
                (current_x + width, miny),
                (current_x + width, maxy),
                (current_x, maxy)
            ])
            # Clip to block
            clipped = lot_poly.intersection(block_geom)
            if not clipped.is_empty:
                result['lots'].append({
                    'geometry': clipped,
                    'width': width
                })
            current_x += width
        
        return result


class LandRedistributionPipeline:
    """Main pipeline orchestrating all optimization stages."""
    
    def __init__(self, land_polygons: List[Polygon], config: Dict[str, Any]):
        """
        Initialize pipeline.
        
        Args:
            land_polygons: Input land plots
            config: Algorithm configuration
        """
        # Merge all input polygons
        from shapely.ops import unary_union
        self.land_poly = unary_union(land_polygons)
        self.config = config
        self.lake_poly = Polygon()  # No lake by default
    
    def run_stage1(self) -> Dict[str, Any]:
        """Run grid optimization stage."""
        optimizer = GridOptimizer(self.land_poly, self.lake_poly)
        
        best_solution, history = optimizer.optimize(
            population_size=self.config.get('population_size', 30),
            generations=self.config.get('generations', 15)
        )
        
        spacing, angle = best_solution
        blocks = optimizer.generate_grid_candidates(spacing, angle)
        
        # Filter to usable blocks
        usable_blocks = []
        for blk in blocks:
            intersection = blk.intersection(self.land_poly).difference(self.lake_poly)
            if not intersection.is_empty:
                usable_blocks.append(intersection)
        
        return {
            'spacing': spacing,
            'angle': angle,
            'blocks': usable_blocks,
            'history': history,
            'metrics': {
                'total_blocks': len(usable_blocks),
                'optimal_spacing': spacing,
                'optimal_angle': angle
            }
        }
    
    def run_stage2(self, blocks: List[Polygon], spacing: float) -> Dict[str, Any]:
        """Run subdivision stage."""
        all_lots = []
        parks = []
        
        for block in blocks:
            result = SubdivisionSolver.subdivide_block(
                block,
                spacing,
                self.config.get('min_lot_width', 5.0),
                self.config.get('max_lot_width', 8.0),
                self.config.get('target_lot_width', 6.0),
                self.config.get('ortools_time_limit', 5)
            )
            
            if result['type'] == 'park':
                parks.append(result['geometry'])
            else:
                all_lots.extend(result['lots'])
        
        return {
            'lots': all_lots,
            'parks': parks,
            'metrics': {
                'total_lots': len(all_lots),
                'total_parks': len(parks),
                'avg_lot_width': np.mean([lot['width'] for lot in all_lots]) if all_lots else 0
            }
        }
    
    def run_full_pipeline(self) -> Dict[str, Any]:
        """Run complete optimization pipeline."""
        # Stage 1: Grid optimization
        stage1_result = self.run_stage1()
        
        # Stage 2: Subdivision
        stage2_result = self.run_stage2(
            stage1_result['blocks'],
            stage1_result['spacing']
        )
        
        return {
            'stage1': stage1_result,
            'stage2': stage2_result,
            'total_lots': stage2_result['metrics']['total_lots']
        }
