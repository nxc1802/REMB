"""
Grid layout optimization using NSGA-II genetic algorithm.

Optimizes grid spacing and rotation angle to maximize usable land area
while minimizing fragmented blocks.
"""

import random
import logging
from typing import List, Tuple, Optional

import numpy as np
from shapely.geometry import Polygon, Point
from shapely.affinity import translate, rotate
from deap import base, creator, tools, algorithms

from core.config.settings import OptimizationSettings, DEFAULT_SETTINGS

logger = logging.getLogger(__name__)


class GridOptimizer:
    """
    Stage 1: Optimize grid layout using NSGA-II genetic algorithm.
    
    Multi-objective optimization:
    - Maximize residential/commercial area
    - Minimize fragmented blocks
    """
    
    def __init__(
        self, 
        land_polygon: Polygon, 
        lake_polygon: Optional[Polygon] = None,
        settings: Optional[OptimizationSettings] = None
    ):
        """
        Initialize grid optimizer.
        
        Args:
            land_polygon: Main land boundary
            lake_polygon: Water body to exclude (optional)
            settings: Optimization settings (uses defaults if None)
        """
        self.land_poly = land_polygon
        self.lake_poly = lake_polygon or Polygon()
        self.settings = settings or DEFAULT_SETTINGS.optimization
        
        self._setup_deap()
    
    def _setup_deap(self) -> None:
        """Configure DEAP toolbox for multi-objective optimization."""
        # Create fitness and individual classes (check if already exists)
        if not hasattr(creator, "FitnessMulti"):
            creator.create("FitnessMulti", base.Fitness, weights=(1.0, -1.0))
        if not hasattr(creator, "Individual"):
            creator.create("Individual", list, fitness=creator.FitnessMulti)
        
        self.toolbox = base.Toolbox()
        
        # Gene definitions
        spacing_min, spacing_max = self.settings.spacing_bounds
        angle_min, angle_max = self.settings.angle_bounds
        
        self.toolbox.register("attr_spacing", random.uniform, spacing_min, spacing_max)
        self.toolbox.register("attr_angle", random.uniform, angle_min, angle_max)
        
        self.toolbox.register(
            "individual", 
            tools.initCycle, 
            creator.Individual,
            (self.toolbox.attr_spacing, self.toolbox.attr_angle), 
            n=1
        )
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        
        # Genetic operators
        self.toolbox.register("evaluate", self._evaluate_layout)
        self.toolbox.register(
            "mate", 
            tools.cxSimulatedBinaryBounded, 
            low=[spacing_min, angle_min], 
            up=[spacing_max, angle_max], 
            eta=self.settings.eta
        )
        self.toolbox.register(
            "mutate", 
            tools.mutPolynomialBounded, 
            low=[spacing_min, angle_min], 
            up=[spacing_max, angle_max], 
            eta=self.settings.eta, 
            indpb=0.2
        )
        self.toolbox.register("select", tools.selNSGA2)
    
    def generate_grid_candidates(
        self, 
        spacing: float, 
        angle_deg: float
    ) -> List[Polygon]:
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
        
        # Create grid ranges (extend beyond bounds to cover after rotation)
        x_range = np.arange(minx - diameter, maxx + diameter, spacing)
        y_range = np.arange(miny - diameter, maxy + diameter, spacing)
        
        blocks = []
        
        # Create base block at origin
        base_block = Polygon([
            (0, 0), 
            (spacing, 0), 
            (spacing, spacing), 
            (0, spacing)
        ])
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
        1. Maximize residential area (positive weight)
        2. Minimize fragmented blocks (negative weight)
        
        Args:
            individual: [spacing, angle]
            
        Returns:
            (total_residential_area, fragmented_blocks)
        """
        spacing, angle = individual
        blocks = self.generate_grid_candidates(spacing, angle)
        
        total_residential_area = 0.0
        fragmented_blocks = 0
        
        original_area = spacing * spacing
        
        for blk in blocks:
            # Cut with land boundary
            intersection = blk.intersection(self.land_poly)
            if intersection.is_empty:
                continue
            
            # Subtract lake/water body
            usable_part = intersection.difference(self.lake_poly)
            if usable_part.is_empty:
                continue
            
            # Calculate area ratio
            ratio = usable_part.area / original_area
            
            # Classify block quality
            if ratio > self.settings.good_block_ratio:
                # Good block for residential/commercial
                total_residential_area += usable_part.area
            elif ratio > self.settings.fragmented_block_ratio:
                # Fragmented block (penalize)
                fragmented_blocks += 1
        
        return (total_residential_area, fragmented_blocks)
    
    def optimize(
        self, 
        population_size: Optional[int] = None, 
        generations: Optional[int] = None
    ) -> Tuple[List[float], List[List[float]]]:
        """
        Run NSGA-II optimization.
        
        Args:
            population_size: Population size (uses settings if None)
            generations: Number of generations (uses settings if None)
            
        Returns:
            (best_solution, history) where best_solution is [spacing, angle]
        """
        pop_size = population_size or self.settings.population_size
        num_gens = generations or self.settings.generations
        
        random.seed(DEFAULT_SETTINGS.random_seed)
        pop = self.toolbox.population(n=pop_size)
        
        history = []
        
        # Initial evaluation
        fits = list(map(self.toolbox.evaluate, pop))
        for ind, fit in zip(pop, fits):
            ind.fitness.values = fit
        
        # Save best from generation 0
        best_ind = tools.selBest(pop, 1)[0]
        history.append(list(best_ind))
        
        # Evolution loop
        for gen in range(num_gens):
            offspring = algorithms.varAnd(
                pop, 
                self.toolbox, 
                cxpb=self.settings.crossover_probability, 
                mutpb=self.settings.mutation_probability
            )
            fits = list(map(self.toolbox.evaluate, offspring))
            for ind, fit in zip(offspring, fits):
                ind.fitness.values = fit
            pop = self.toolbox.select(pop + offspring, k=len(pop))
            
            # Track best solution per generation
            best_ind = tools.selBest(pop, 1)[0]
            history.append(list(best_ind))
        
        final_best = tools.selBest(pop, 1)[0]
        logger.info(f"Optimization complete: spacing={final_best[0]:.2f}, angle={final_best[1]:.2f}")
        
        return list(final_best), history
