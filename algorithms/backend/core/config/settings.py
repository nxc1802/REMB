"""
Algorithm configuration settings and constants.

Contains all configurable parameters for the land redistribution algorithm,
organized into dataclasses for type safety and clarity.
"""

from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class RoadSettings:
    """Road and transportation infrastructure settings (TCVN standards)."""
    
    # Road widths (meters)
    main_width: float = 30.0       # Main road - container trucks can pass
    internal_width: float = 15.0   # Internal road
    sidewalk_width: float = 4.0    # Sidewalk each side (includes utility trench)
    turning_radius: float = 15.0   # Corner chamfer radius for intersections


@dataclass(frozen=True)
class SubdivisionSettings:
    """Block and lot subdivision settings."""
    
    # Land allocation
    service_area_ratio: float = 0.10    # 10% for infrastructure (WWTP, parking, etc.)
    min_block_area: float = 5000.0      # Minimum block area to subdivide (m²)
    
    # Lot dimensions (industrial)
    min_lot_width: float = 20.0         # Minimum lot frontage (m)
    max_lot_width: float = 80.0         # Maximum lot frontage (m)
    target_lot_width: float = 40.0      # Target lot width (m)
    
    # Legal/Construction (TCVN)
    setback_distance: float = 6.0       # Building setback from road (m)
    fire_safety_gap: float = 4.0        # Fire safety gap between buildings (m)
    
    # Solver
    solver_time_limit: float = 0.5      # OR-Tools time limit per block (seconds)


@dataclass(frozen=True)
class InfrastructureSettings:
    """Infrastructure planning settings."""
    
    # Electrical
    transformer_radius: float = 300.0   # Effective service radius (m)
    lots_per_transformer: int = 15      # Approximate lots per transformer
    
    # Network
    loop_redundancy_ratio: float = 0.15 # 15% extra edges for loop network safety
    max_connection_distance: float = 500.0  # Max distance for lot connections (m)
    
    # Drainage
    drainage_arrow_length: float = 30.0 # Arrow length for visualization (m)


@dataclass(frozen=True)
class OptimizationSettings:
    """NSGA-II genetic algorithm settings."""
    
    # Population
    population_size: int = 30
    generations: int = 15
    
    # Crossover/Mutation
    crossover_probability: float = 0.7
    mutation_probability: float = 0.3
    eta: float = 20.0  # Distribution index for SBX crossover
    
    # Gene bounds
    spacing_bounds: Tuple[float, float] = (20.0, 40.0)
    angle_bounds: Tuple[float, float] = (0.0, 90.0)
    
    # Block quality thresholds
    good_block_ratio: float = 0.65      # Ratio for residential/commercial
    fragmented_block_ratio: float = 0.1 # Below this = too small


@dataclass
class AlgorithmSettings:
    """Complete algorithm configuration."""
    
    road: RoadSettings = field(default_factory=RoadSettings)
    subdivision: SubdivisionSettings = field(default_factory=SubdivisionSettings)
    infrastructure: InfrastructureSettings = field(default_factory=InfrastructureSettings)
    optimization: OptimizationSettings = field(default_factory=OptimizationSettings)
    
    # Random seed for reproducibility
    random_seed: int = 42
    
    @classmethod
    def from_dict(cls, config: dict) -> 'AlgorithmSettings':
        """Create settings from API config dictionary."""
        settings = cls()
        
        # Map API config to internal settings
        if 'min_lot_width' in config:
            settings = cls(
                subdivision=SubdivisionSettings(
                    min_lot_width=config.get('min_lot_width', 20.0),
                    max_lot_width=config.get('max_lot_width', 80.0),
                    target_lot_width=config.get('target_lot_width', 40.0),
                    solver_time_limit=config.get('ortools_time_limit', 0.5),
                ),
                optimization=OptimizationSettings(
                    population_size=config.get('population_size', 30),
                    generations=config.get('generations', 15),
                ),
            )
        
        return settings


# Default settings instance
DEFAULT_SETTINGS = AlgorithmSettings()


# Convenience accessors for backward compatibility
ROAD_MAIN_WIDTH = DEFAULT_SETTINGS.road.main_width
ROAD_INTERNAL_WIDTH = DEFAULT_SETTINGS.road.internal_width
SIDEWALK_WIDTH = DEFAULT_SETTINGS.road.sidewalk_width
TURNING_RADIUS = DEFAULT_SETTINGS.road.turning_radius
SERVICE_AREA_RATIO = DEFAULT_SETTINGS.subdivision.service_area_ratio
MIN_BLOCK_AREA = DEFAULT_SETTINGS.subdivision.min_block_area
MIN_LOT_WIDTH = DEFAULT_SETTINGS.subdivision.min_lot_width
MAX_LOT_WIDTH = DEFAULT_SETTINGS.subdivision.max_lot_width
TARGET_LOT_WIDTH = DEFAULT_SETTINGS.subdivision.target_lot_width
SETBACK_DISTANCE = DEFAULT_SETTINGS.subdivision.setback_distance
FIRE_SAFETY_GAP = DEFAULT_SETTINGS.subdivision.fire_safety_gap
SOLVER_TIME_LIMIT = DEFAULT_SETTINGS.subdivision.solver_time_limit
TRANSFORMER_RADIUS = DEFAULT_SETTINGS.infrastructure.transformer_radius
