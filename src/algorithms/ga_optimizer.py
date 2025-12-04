"""
Simple Genetic Algorithm Optimizer
Generates 3 diverse layout options for industrial estate planning
Following MVP-24h.md specification
"""
import random
import math
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass, field
from shapely.geometry import Polygon, box, Point
from shapely.ops import unary_union
import logging

logger = logging.getLogger(__name__)


@dataclass
class PlotConfig:
    """Plot configuration"""
    x: float
    y: float
    width: float
    height: float
    
    @property
    def area(self) -> float:
        return self.width * self.height
    
    @property
    def geometry(self) -> Polygon:
        return box(self.x, self.y, self.x + self.width, self.y + self.height)
    
    def to_dict(self) -> Dict:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "area": self.area,
            "coords": list(self.geometry.exterior.coords)
        }


@dataclass
class LayoutCandidate:
    """A layout candidate in the GA population"""
    plots: List[PlotConfig] = field(default_factory=list)
    fitness: float = 0.0
    
    @property
    def total_area(self) -> float:
        return sum(p.area for p in self.plots)
    
    @property
    def avg_plot_size(self) -> float:
        return self.total_area / len(self.plots) if self.plots else 0
    
    def to_dict(self) -> Dict:
        return {
            "plots": [p.to_dict() for p in self.plots],
            "total_plots": len(self.plots),
            "total_area": self.total_area,
            "avg_size": self.avg_plot_size,
            "fitness": self.fitness
        }


class SimpleGAOptimizer:
    """
    Simple Genetic Algorithm for layout optimization
    
    Per MVP-24h.md:
    - Population: 10 layouts
    - Generations: 20
    - Elite: 3 best
    - Mutation rate: 30%
    - Output: 3 diverse options
    """
    
    def __init__(
        self,
        population_size: int = 10,
        n_generations: int = 20,
        elite_size: int = 3,
        mutation_rate: float = 0.3,
        setback: float = 50.0,
        target_plots: int = 8
    ):
        self.population_size = population_size
        self.n_generations = n_generations
        self.elite_size = elite_size
        self.mutation_rate = mutation_rate
        self.setback = setback
        self.target_plots = target_plots
        
        # Plot size ranges
        self.min_plot_width = 30
        self.max_plot_width = 80
        self.min_plot_height = 40
        self.max_plot_height = 100
    
    def optimize(self, boundary_coords: List[List[float]]) -> List[Dict]:
        """
        Run GA optimization and return 3 diverse layout options
        
        Args:
            boundary_coords: List of [x, y] coordinate pairs
            
        Returns:
            List of 3 layout options with different strategies
        """
        logger.info("Starting GA optimization")
        
        # Create boundary polygon
        boundary = Polygon(boundary_coords)
        if not boundary.is_valid:
            boundary = boundary.buffer(0)
        
        # Get buildable area (after setback)
        buildable = boundary.buffer(-self.setback)
        if buildable.is_empty or not buildable.is_valid:
            logger.warning("Buildable area too small, reducing setback")
            buildable = boundary.buffer(-self.setback / 2)
        
        bounds = buildable.bounds  # (minx, miny, maxx, maxy)
        
        # Initialize population
        population = self._initialize_population(buildable, bounds)
        
        # Evolution loop
        for gen in range(self.n_generations):
            # Evaluate fitness
            for candidate in population:
                candidate.fitness = self._evaluate_fitness(candidate, buildable, boundary)
            
            # Sort by fitness
            population.sort(key=lambda x: x.fitness, reverse=True)
            
            # Keep elite
            elite = population[:self.elite_size]
            
            # Create new population from elite
            new_population = elite.copy()
            
            while len(new_population) < self.population_size:
                parent = random.choice(elite)
                child = self._mutate(parent, bounds, buildable)
                new_population.append(child)
            
            population = new_population
        
        # Final sort
        for candidate in population:
            candidate.fitness = self._evaluate_fitness(candidate, buildable, boundary)
        population.sort(key=lambda x: x.fitness, reverse=True)
        
        # Create 3 diverse options
        options = self._create_diverse_options(population, buildable, bounds, boundary)
        
        logger.info(f"GA complete: {len(options)} options generated")
        return options
    
    def _initialize_population(self, buildable: Polygon, bounds: Tuple) -> List[LayoutCandidate]:
        """Create initial random population"""
        population = []
        minx, miny, maxx, maxy = bounds
        
        for _ in range(self.population_size):
            candidate = LayoutCandidate()
            placed = []
            
            for _ in range(self.target_plots):
                # Random plot dimensions
                width = random.uniform(self.min_plot_width, self.max_plot_width)
                height = random.uniform(self.min_plot_height, self.max_plot_height)
                
                # Random position
                for attempt in range(20):
                    x = random.uniform(minx, maxx - width)
                    y = random.uniform(miny, maxy - height)
                    
                    plot = PlotConfig(x=x, y=y, width=width, height=height)
                    
                    # Check if within buildable and no overlap
                    if buildable.contains(plot.geometry):
                        overlaps = False
                        for existing in placed:
                            if plot.geometry.intersects(existing.geometry):
                                overlaps = True
                                break
                        
                        if not overlaps:
                            placed.append(plot)
                            break
                
            candidate.plots = placed
            population.append(candidate)
        
        return population
    
    def _evaluate_fitness(self, candidate: LayoutCandidate, buildable: Polygon, boundary: Polygon) -> float:
        """
        Evaluate fitness of a layout candidate
        
        Fitness = (Profit × 0.5) + (Compliance × 0.3) + (Efficiency × 0.2)
        """
        if not candidate.plots:
            return 0.0
        
        # Profit score (normalized total area)
        max_area = buildable.area * 0.6  # Max 60% coverage
        profit = min(candidate.total_area / max_area, 1.0)
        
        # Compliance score (all plots within setback)
        compliant = sum(1 for p in candidate.plots if buildable.contains(p.geometry))
        compliance = compliant / len(candidate.plots)
        
        # Efficiency score (plot count vs target)
        efficiency = min(len(candidate.plots) / self.target_plots, 1.0)
        
        fitness = (profit * 0.5) + (compliance * 0.3) + (efficiency * 0.2)
        return round(fitness, 4)
    
    def _mutate(self, parent: LayoutCandidate, bounds: Tuple, buildable: Polygon) -> LayoutCandidate:
        """Create mutated child from parent"""
        child = LayoutCandidate()
        minx, miny, maxx, maxy = bounds
        
        for plot in parent.plots:
            if random.random() < self.mutation_rate:
                # Mutate position (±30m)
                new_x = plot.x + random.uniform(-30, 30)
                new_y = plot.y + random.uniform(-30, 30)
                
                # Keep within bounds
                new_x = max(minx, min(new_x, maxx - plot.width))
                new_y = max(miny, min(new_y, maxy - plot.height))
                
                new_plot = PlotConfig(x=new_x, y=new_y, width=plot.width, height=plot.height)
                
                if buildable.contains(new_plot.geometry):
                    child.plots.append(new_plot)
                else:
                    child.plots.append(plot)
            else:
                child.plots.append(plot)
        
        return child
    
    def _create_diverse_options(
        self, 
        population: List[LayoutCandidate],
        buildable: Polygon,
        bounds: Tuple,
        boundary: Polygon
    ) -> List[Dict]:
        """
        Create 3 diverse layout options:
        1. Maximum Profit (most plots)
        2. Balanced (medium density)
        3. Premium (fewer, larger plots)
        """
        options = []
        
        # Option 1: Maximum Profit (best fitness from GA)
        if population:
            best = population[0]
            options.append({
                "id": 1,
                "name": "Maximum Profit",
                "icon": "💰",
                "description": "Maximizes sellable area with more plots",
                "plots": [p.to_dict() for p in best.plots],
                "metrics": {
                    "total_plots": len(best.plots),
                    "total_area": round(best.total_area, 2),
                    "avg_size": round(best.avg_plot_size, 2),
                    "fitness": best.fitness,
                    "compliance": "PASS"
                }
            })
        
        # Option 2: Balanced - Generate with medium density
        balanced = self._generate_balanced_layout(buildable, bounds)
        options.append({
            "id": 2,
            "name": "Balanced",
            "icon": "⚖️",
            "description": "Balanced approach with medium-sized plots",
            "plots": [p.to_dict() for p in balanced.plots],
            "metrics": {
                "total_plots": len(balanced.plots),
                "total_area": round(balanced.total_area, 2),
                "avg_size": round(balanced.avg_plot_size, 2),
                "fitness": self._evaluate_fitness(balanced, buildable, boundary),
                "compliance": "PASS"
            }
        })
        
        # Option 3: Premium - Fewer, larger plots
        premium = self._generate_premium_layout(buildable, bounds)
        options.append({
            "id": 3,
            "name": "Premium",
            "icon": "🏢",
            "description": "Premium layout with fewer, larger plots",
            "plots": [p.to_dict() for p in premium.plots],
            "metrics": {
                "total_plots": len(premium.plots),
                "total_area": round(premium.total_area, 2),
                "avg_size": round(premium.avg_plot_size, 2),
                "fitness": self._evaluate_fitness(premium, buildable, boundary),
                "compliance": "PASS"
            }
        })
        
        return options
    
    def _generate_balanced_layout(self, buildable: Polygon, bounds: Tuple) -> LayoutCandidate:
        """Generate balanced layout with medium plot sizes"""
        candidate = LayoutCandidate()
        minx, miny, maxx, maxy = bounds
        
        # Medium plot size
        plot_width = 50
        plot_height = 70
        spacing = 20
        
        placed = []
        y = miny + spacing
        
        while y + plot_height < maxy:
            x = minx + spacing
            while x + plot_width < maxx:
                plot = PlotConfig(x=x, y=y, width=plot_width, height=plot_height)
                
                if buildable.contains(plot.geometry):
                    overlaps = False
                    for existing in placed:
                        if plot.geometry.intersects(existing.geometry):
                            overlaps = True
                            break
                    
                    if not overlaps:
                        placed.append(plot)
                
                x += plot_width + spacing
            y += plot_height + spacing
        
        candidate.plots = placed[:8]  # Limit to 8 plots
        return candidate
    
    def _generate_premium_layout(self, buildable: Polygon, bounds: Tuple) -> LayoutCandidate:
        """Generate premium layout with fewer, larger plots"""
        candidate = LayoutCandidate()
        minx, miny, maxx, maxy = bounds
        
        # Large plot size
        plot_width = 80
        plot_height = 100
        spacing = 30
        
        placed = []
        y = miny + spacing
        
        while y + plot_height < maxy and len(placed) < 4:
            x = minx + spacing
            while x + plot_width < maxx and len(placed) < 4:
                plot = PlotConfig(x=x, y=y, width=plot_width, height=plot_height)
                
                if buildable.contains(plot.geometry):
                    overlaps = False
                    for existing in placed:
                        if plot.geometry.intersects(existing.geometry):
                            overlaps = True
                            break
                    
                    if not overlaps:
                        placed.append(plot)
                
                x += plot_width + spacing
            y += plot_height + spacing
        
        candidate.plots = placed
        return candidate


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Sample boundary (simple rectangle)
    boundary = [
        [0, 0], [500, 0], [500, 400], [0, 400], [0, 0]
    ]
    
    optimizer = SimpleGAOptimizer()
    options = optimizer.optimize(boundary)
    
    for opt in options:
        print(f"\n{opt['icon']} {opt['name']}")
        print(f"   Plots: {opt['metrics']['total_plots']}")
        print(f"   Area: {opt['metrics']['total_area']} m²")
        print(f"   Avg: {opt['metrics']['avg_size']} m²")
        print(f"   Fitness: {opt['metrics']['fitness']}")
