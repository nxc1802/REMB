"""Tile System module for Wave Function Collapse.

Contains algorithms for tile-based detail generation:
- WFC Solver for constraint propagation
- Tile Registry for tile definitions
- Pre-made tile templates for various zone types
"""

from .tile_registry import (
    Tile,
    TileEdge,
    TileRegistry,
    get_tile_registry,
    create_industrial_tiles,
    create_residential_tiles,
    INDUSTRIAL_TILES,
    RESIDENTIAL_TILES
)

from .wfc_solver import (
    WFCSolver,
    WFCConfig,
    WFCCell,
    solve_wfc
)

__all__ = [
    # Registry
    "Tile",
    "TileEdge",
    "TileRegistry",
    "get_tile_registry",
    "create_industrial_tiles",
    "create_residential_tiles",
    "INDUSTRIAL_TILES",
    "RESIDENTIAL_TILES",
    # Solver
    "WFCSolver",
    "WFCConfig",
    "WFCCell",
    "solve_wfc"
]
