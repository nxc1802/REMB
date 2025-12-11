"""Tile definitions and registry for WFC.

Defines tiles, their adjacency rules, and provides a registry
for managing tile sets for different zone types.

Reference: docs/Procedural Generation.md - Section 3 (Wave Function Collapse)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum, auto
import logging

logger = logging.getLogger(__name__)


class TileEdge(Enum):
    """Edge types for tile adjacency matching."""
    EMPTY = auto()      # Empty/grass
    ROAD = auto()       # Road connection
    BUILDING = auto()   # Building edge
    FENCE = auto()      # Fence/boundary
    GREEN = auto()      # Green space
    PARKING = auto()    # Parking area


@dataclass
class Tile:
    """A single tile definition.
    
    Each tile has:
    - A unique ID
    - Edge types for each direction (N, E, S, W)
    - Weight for random selection
    - Properties (building type, area requirements, etc.)
    """
    
    id: str
    name: str
    
    # Edges: (North, East, South, West)
    edges: Tuple[TileEdge, TileEdge, TileEdge, TileEdge]
    
    # Selection weight (higher = more likely)
    weight: float = 1.0
    
    # Size in grid units (default 1x1)
    width: int = 1
    height: int = 1
    
    # Properties
    properties: Dict = field(default_factory=dict)
    
    def can_connect(self, other: 'Tile', direction: str) -> bool:
        """Check if this tile can connect to another in given direction.
        
        Args:
            other: Other tile to check
            direction: 'N', 'E', 'S', or 'W'
            
        Returns:
            True if edges are compatible
        """
        dir_idx = {'N': 0, 'E': 1, 'S': 2, 'W': 3}
        opp_idx = {'N': 2, 'E': 3, 'S': 0, 'W': 1}
        
        my_edge = self.edges[dir_idx[direction]]
        their_edge = other.edges[opp_idx[direction]]
        
        # Same edge type = compatible
        return my_edge == their_edge
        
    def rotate(self, times: int = 1) -> 'Tile':
        """Create a rotated version of this tile.
        
        Args:
            times: Number of 90-degree clockwise rotations
            
        Returns:
            New rotated tile
        """
        edges = list(self.edges)
        for _ in range(times % 4):
            edges = [edges[3], edges[0], edges[1], edges[2]]
            
        return Tile(
            id=f"{self.id}_r{times}",
            name=f"{self.name} (rotated {times*90}°)",
            edges=tuple(edges),
            weight=self.weight,
            width=self.height if times % 2 else self.width,
            height=self.width if times % 2 else self.height,
            properties=dict(self.properties)
        )


class TileRegistry:
    """Registry for managing tile sets.
    
    Provides pre-defined tile sets for different zone types
    and methods for adding custom tiles.
    """
    
    def __init__(self):
        self.tiles: Dict[str, Tile] = {}
        self.tile_sets: Dict[str, List[str]] = {}
        
    def register(self, tile: Tile, tile_set: str = "default"):
        """Register a tile.
        
        Args:
            tile: Tile to register
            tile_set: Name of tile set to add to
        """
        self.tiles[tile.id] = tile
        
        if tile_set not in self.tile_sets:
            self.tile_sets[tile_set] = []
        self.tile_sets[tile_set].append(tile.id)
        
    def get(self, tile_id: str) -> Optional[Tile]:
        """Get a tile by ID."""
        return self.tiles.get(tile_id)
        
    def get_tile_set(self, name: str) -> List[Tile]:
        """Get all tiles in a tile set."""
        if name not in self.tile_sets:
            return []
        return [self.tiles[tid] for tid in self.tile_sets[name]]
        
    def get_compatible(
        self, 
        tile: Tile, 
        direction: str,
        tile_set: str = "default"
    ) -> List[Tile]:
        """Get all tiles compatible with given tile in direction.
        
        Args:
            tile: Source tile
            direction: Direction to check
            tile_set: Tile set to search
            
        Returns:
            List of compatible tiles
        """
        candidates = self.get_tile_set(tile_set)
        return [t for t in candidates if tile.can_connect(t, direction)]


# === Pre-defined Tiles ===

def create_industrial_tiles() -> TileRegistry:
    """Create tile set for industrial parks.
    
    Returns:
        TileRegistry with industrial tiles
    """
    registry = TileRegistry()
    
    # Empty/grass tile
    registry.register(Tile(
        id="empty",
        name="Empty Grass",
        edges=(TileEdge.EMPTY, TileEdge.EMPTY, TileEdge.EMPTY, TileEdge.EMPTY),
        weight=2.0,
        properties={"type": "green"}
    ), "industrial")
    
    # Road tiles
    registry.register(Tile(
        id="road_straight_h",
        name="Road Straight (H)",
        edges=(TileEdge.EMPTY, TileEdge.ROAD, TileEdge.EMPTY, TileEdge.ROAD),
        weight=1.5,
        properties={"type": "road", "direction": "horizontal"}
    ), "industrial")
    
    registry.register(Tile(
        id="road_straight_v",
        name="Road Straight (V)",
        edges=(TileEdge.ROAD, TileEdge.EMPTY, TileEdge.ROAD, TileEdge.EMPTY),
        weight=1.5,
        properties={"type": "road", "direction": "vertical"}
    ), "industrial")
    
    registry.register(Tile(
        id="road_corner_ne",
        name="Road Corner NE",
        edges=(TileEdge.ROAD, TileEdge.ROAD, TileEdge.EMPTY, TileEdge.EMPTY),
        weight=1.0,
        properties={"type": "road", "corner": "NE"}
    ), "industrial")
    
    registry.register(Tile(
        id="road_corner_se",
        name="Road Corner SE",
        edges=(TileEdge.EMPTY, TileEdge.ROAD, TileEdge.ROAD, TileEdge.EMPTY),
        weight=1.0,
        properties={"type": "road", "corner": "SE"}
    ), "industrial")
    
    registry.register(Tile(
        id="road_corner_sw",
        name="Road Corner SW",
        edges=(TileEdge.EMPTY, TileEdge.EMPTY, TileEdge.ROAD, TileEdge.ROAD),
        weight=1.0,
        properties={"type": "road", "corner": "SW"}
    ), "industrial")
    
    registry.register(Tile(
        id="road_corner_nw",
        name="Road Corner NW",
        edges=(TileEdge.ROAD, TileEdge.EMPTY, TileEdge.EMPTY, TileEdge.ROAD),
        weight=1.0,
        properties={"type": "road", "corner": "NW"}
    ), "industrial")
    
    registry.register(Tile(
        id="road_t_north",
        name="Road T North",
        edges=(TileEdge.ROAD, TileEdge.ROAD, TileEdge.EMPTY, TileEdge.ROAD),
        weight=0.8,
        properties={"type": "road", "intersection": "T"}
    ), "industrial")
    
    registry.register(Tile(
        id="road_cross",
        name="Road Cross",
        edges=(TileEdge.ROAD, TileEdge.ROAD, TileEdge.ROAD, TileEdge.ROAD),
        weight=0.5,
        properties={"type": "road", "intersection": "cross"}
    ), "industrial")
    
    # Building tiles
    registry.register(Tile(
        id="factory_small",
        name="Small Factory",
        edges=(TileEdge.BUILDING, TileEdge.BUILDING, TileEdge.ROAD, TileEdge.BUILDING),
        weight=1.2,
        properties={"type": "building", "subtype": "factory", "size": "small"}
    ), "industrial")
    
    registry.register(Tile(
        id="warehouse",
        name="Warehouse",
        edges=(TileEdge.BUILDING, TileEdge.BUILDING, TileEdge.ROAD, TileEdge.BUILDING),
        weight=1.0,
        properties={"type": "building", "subtype": "warehouse"}
    ), "industrial")
    
    # Parking lot
    registry.register(Tile(
        id="parking_lot",
        name="Parking Lot",
        edges=(TileEdge.PARKING, TileEdge.PARKING, TileEdge.ROAD, TileEdge.PARKING),
        weight=0.8,
        properties={"type": "parking"}
    ), "industrial")
    
    # Guard house
    registry.register(Tile(
        id="guard_house",
        name="Guard House",
        edges=(TileEdge.ROAD, TileEdge.FENCE, TileEdge.FENCE, TileEdge.FENCE),
        weight=0.3,
        properties={"type": "security", "subtype": "guard_house"}
    ), "industrial")
    
    # Green buffer
    registry.register(Tile(
        id="green_buffer",
        name="Green Buffer",
        edges=(TileEdge.GREEN, TileEdge.GREEN, TileEdge.GREEN, TileEdge.GREEN),
        weight=1.5,
        properties={"type": "green", "subtype": "buffer"}
    ), "industrial")
    
    return registry


def create_residential_tiles() -> TileRegistry:
    """Create tile set for residential areas.
    
    Returns:
        TileRegistry with residential tiles
    """
    registry = TileRegistry()
    
    # Basic tiles
    registry.register(Tile(
        id="empty",
        name="Empty Lot",
        edges=(TileEdge.EMPTY, TileEdge.EMPTY, TileEdge.EMPTY, TileEdge.EMPTY),
        weight=1.0,
        properties={"type": "empty"}
    ), "residential")
    
    registry.register(Tile(
        id="house_single",
        name="Single House",
        edges=(TileEdge.FENCE, TileEdge.FENCE, TileEdge.ROAD, TileEdge.FENCE),
        weight=2.0,
        properties={"type": "building", "subtype": "house_single"}
    ), "residential")
    
    registry.register(Tile(
        id="house_corner",
        name="Corner House",
        edges=(TileEdge.FENCE, TileEdge.ROAD, TileEdge.ROAD, TileEdge.FENCE),
        weight=0.8,
        properties={"type": "building", "subtype": "house_corner"}
    ), "residential")
    
    registry.register(Tile(
        id="park_small",
        name="Small Park",
        edges=(TileEdge.GREEN, TileEdge.GREEN, TileEdge.ROAD, TileEdge.GREEN),
        weight=0.5,
        properties={"type": "green", "subtype": "park"}
    ), "residential")
    
    # Road tiles
    registry.register(Tile(
        id="road_straight_h",
        name="Road Straight (H)",
        edges=(TileEdge.FENCE, TileEdge.ROAD, TileEdge.FENCE, TileEdge.ROAD),
        weight=1.5,
        properties={"type": "road"}
    ), "residential")
    
    return registry


# Default registries
INDUSTRIAL_TILES = create_industrial_tiles()
RESIDENTIAL_TILES = create_residential_tiles()


def get_tile_registry(zone_type: str = "industrial") -> TileRegistry:
    """Get tile registry for zone type.
    
    Args:
        zone_type: 'industrial' or 'residential'
        
    Returns:
        Appropriate TileRegistry
    """
    if zone_type == "residential":
        return RESIDENTIAL_TILES
    return INDUSTRIAL_TILES
