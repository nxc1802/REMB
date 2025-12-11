"""Wave Function Collapse solver for tile placement.

Implements the WFC algorithm for filling a grid with tiles
while respecting adjacency constraints.

Reference: docs/Procedural Generation.md - Section 3 (Wave Function Collapse)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
import numpy as np
import logging
from shapely.geometry import Polygon, box

from .tile_registry import Tile, TileRegistry, TileEdge, get_tile_registry

logger = logging.getLogger(__name__)


@dataclass
class WFCConfig:
    """Configuration for WFC solver."""
    
    # Grid settings
    tile_size: float = 10.0  # meters per tile
    
    # Solver limits
    max_iterations: int = 10000
    max_backtrack: int = 100
    
    # Tile set
    tile_set: str = "industrial"
    
    # Random seed for reproducibility
    seed: Optional[int] = None
    
    # Adaptive sizing
    adaptive_sizing: bool = True
    min_tile_size: float = 5.0   # meters
    max_tile_size: float = 50.0  # meters


@dataclass
class WFCCell:
    """A single cell in the WFC grid."""
    
    row: int
    col: int
    
    # Possible tiles (starts with all, collapses to one)
    possibilities: Set[str] = field(default_factory=set)
    
    # Collapsed tile (None if not yet collapsed)
    collapsed_tile: Optional[Tile] = None
    
    @property
    def is_collapsed(self) -> bool:
        return self.collapsed_tile is not None
        
    @property
    def entropy(self) -> int:
        """Number of remaining possibilities."""
        if self.is_collapsed:
            return 0
        return len(self.possibilities)


class WFCSolver:
    """Wave Function Collapse algorithm for tile placement.
    
    Algorithm:
    1. Initialize grid with all tiles as possibilities
    2. While uncollapsed cells remain:
       a. Find cell with lowest entropy (fewest possibilities)
       b. Collapse it to a random tile (weighted by tile.weight)
       c. Propagate constraints to neighbors
       d. If contradiction, backtrack
    3. Return filled grid
    
    Example:
        >>> solver = WFCSolver(lot_polygon, config)
        >>> result = solver.solve()
        >>> for cell in result:
        ...     print(cell.collapsed_tile.name)
    """
    
    def __init__(
        self,
        boundary: Polygon,
        config: Optional[WFCConfig] = None,
        registry: Optional[TileRegistry] = None
    ):
        """Initialize WFC solver.
        
        Args:
            boundary: Polygon to fill with tiles
            config: WFC configuration
            registry: Tile registry to use
        """
        self.boundary = boundary
        self.config = config or WFCConfig()
        
        # Get tile registry
        if registry:
            self.registry = registry
        else:
            self.registry = get_tile_registry(self.config.tile_set)
            
        # Setup random generator
        self.rng = np.random.default_rng(self.config.seed)
        
        # Calculate grid dimensions
        self._setup_grid()
        
        # Precompute adjacency rules
        self._precompute_adjacency()
        
    def _setup_grid(self):
        """Setup the grid based on boundary and tile size."""
        minx, miny, maxx, maxy = self.boundary.bounds
        self.minx, self.miny = minx, miny
        
        # Adaptive tile sizing
        tile_size = self.config.tile_size
        
        if self.config.adaptive_sizing:
            width = maxx - minx
            height = maxy - miny
            area = self.boundary.area
            
            # Target roughly 100-400 tiles
            target_tiles = 200
            optimal_size = np.sqrt(area / target_tiles)
            
            tile_size = np.clip(
                optimal_size,
                self.config.min_tile_size,
                self.config.max_tile_size
            )
            
            logger.debug(f"Adaptive tile size: {tile_size:.1f}m")
            
        self.tile_size = tile_size
        
        # Grid dimensions
        self.cols = max(1, int((maxx - minx) / tile_size))
        self.rows = max(1, int((maxy - miny) / tile_size))
        
        logger.info(f"WFC grid: {self.rows}x{self.cols} = {self.rows * self.cols} cells")
        
        # Initialize grid
        all_tile_ids = set(t.id for t in self.registry.get_tile_set(self.config.tile_set))
        
        self.grid: List[List[WFCCell]] = []
        for r in range(self.rows):
            row = []
            for c in range(self.cols):
                cell = WFCCell(
                    row=r,
                    col=c,
                    possibilities=set(all_tile_ids)
                )
                
                # Check if cell is within boundary
                cell_poly = self._cell_to_polygon(r, c)
                if not cell_poly.intersects(self.boundary):
                    # Outside boundary - collapse to empty
                    cell.possibilities = set()
                    cell.collapsed_tile = self.registry.get("empty")
                    
                row.append(cell)
            self.grid.append(row)
            
    def _cell_to_polygon(self, row: int, col: int) -> Polygon:
        """Convert grid cell to world polygon."""
        x = self.minx + col * self.tile_size
        y = self.miny + row * self.tile_size
        return box(x, y, x + self.tile_size, y + self.tile_size)
        
    def _precompute_adjacency(self):
        """Precompute which tiles can be adjacent to which."""
        tiles = self.registry.get_tile_set(self.config.tile_set)
        
        # adjacency[tile_id][direction] = set of compatible tile_ids
        self.adjacency: Dict[str, Dict[str, Set[str]]] = {}
        
        for tile in tiles:
            self.adjacency[tile.id] = {
                'N': set(),
                'E': set(),
                'S': set(),
                'W': set()
            }
            
            for other in tiles:
                for direction in ['N', 'E', 'S', 'W']:
                    if tile.can_connect(other, direction):
                        self.adjacency[tile.id][direction].add(other.id)
                        
    def solve(self) -> List[WFCCell]:
        """Run WFC algorithm.
        
        Returns:
            List of all collapsed cells
        """
        iteration = 0
        backtrack_count = 0
        history = []  # For backtracking
        
        while iteration < self.config.max_iterations:
            iteration += 1
            
            # Find uncollapsed cell with minimum entropy
            cell = self._find_min_entropy_cell()
            
            if cell is None:
                # All cells collapsed - success!
                logger.info(f"WFC solved in {iteration} iterations")
                break
                
            if cell.entropy == 0:
                # Contradiction - backtrack
                if backtrack_count >= self.config.max_backtrack:
                    logger.warning("WFC backtrack limit reached")
                    break
                    
                if history:
                    self._backtrack(history)
                    backtrack_count += 1
                    continue
                else:
                    logger.warning("WFC contradiction with no history")
                    break
                    
            # Save state for backtracking
            history.append(self._save_state())
            
            # Collapse cell
            self._collapse_cell(cell)
            
            # Propagate constraints
            self._propagate(cell)
            
        # Return all cells
        result = []
        for row in self.grid:
            for cell in row:
                result.append(cell)
                
        return result
        
    def _find_min_entropy_cell(self) -> Optional[WFCCell]:
        """Find uncollapsed cell with lowest entropy."""
        min_entropy = float('inf')
        candidates = []
        
        for row in self.grid:
            for cell in row:
                if not cell.is_collapsed and cell.entropy > 0:
                    if cell.entropy < min_entropy:
                        min_entropy = cell.entropy
                        candidates = [cell]
                    elif cell.entropy == min_entropy:
                        candidates.append(cell)
                        
        if not candidates:
            return None
            
        # Random selection among ties
        return self.rng.choice(candidates)
        
    def _collapse_cell(self, cell: WFCCell):
        """Collapse a cell to a single tile."""
        if not cell.possibilities:
            return
            
        # Get tiles with weights
        tiles = [self.registry.get(tid) for tid in cell.possibilities]
        weights = [t.weight if t else 1.0 for t in tiles]
        
        # Normalize weights
        total = sum(weights)
        probs = [w / total for w in weights]
        
        # Random selection
        idx = self.rng.choice(len(tiles), p=probs)
        chosen = tiles[idx]
        
        cell.collapsed_tile = chosen
        cell.possibilities = {chosen.id} if chosen else set()
        
    def _propagate(self, start_cell: WFCCell):
        """Propagate constraints from collapsed cell."""
        # BFS propagation
        queue = [(start_cell.row, start_cell.col)]
        visited = set()
        
        while queue:
            r, c = queue.pop(0)
            
            if (r, c) in visited:
                continue
            visited.add((r, c))
            
            cell = self.grid[r][c]
            
            if not cell.is_collapsed:
                continue
                
            # Check all neighbors
            neighbors = [
                (r - 1, c, 'N', 'S'),  # North neighbor
                (r + 1, c, 'S', 'N'),  # South neighbor
                (r, c + 1, 'E', 'W'),  # East neighbor
                (r, c - 1, 'W', 'E'),  # West neighbor
            ]
            
            for nr, nc, my_dir, their_dir in neighbors:
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    neighbor = self.grid[nr][nc]
                    
                    if neighbor.is_collapsed:
                        continue
                        
                    # Constrain neighbor possibilities
                    allowed = self.adjacency.get(cell.collapsed_tile.id, {}).get(my_dir, set())
                    
                    old_count = len(neighbor.possibilities)
                    neighbor.possibilities &= allowed
                    
                    if len(neighbor.possibilities) < old_count:
                        queue.append((nr, nc))
                        
    def _save_state(self) -> Dict:
        """Save current grid state for backtracking."""
        state = {}
        for r, row in enumerate(self.grid):
            for c, cell in enumerate(row):
                state[(r, c)] = {
                    'possibilities': set(cell.possibilities),
                    'collapsed_tile': cell.collapsed_tile
                }
        return state
        
    def _backtrack(self, history: List[Dict]):
        """Restore previous state."""
        if not history:
            return
            
        state = history.pop()
        
        for (r, c), data in state.items():
            cell = self.grid[r][c]
            cell.possibilities = data['possibilities']
            cell.collapsed_tile = data['collapsed_tile']
            
    def get_result_polygons(self) -> Dict[str, List[Polygon]]:
        """Convert solved grid to polygons by tile type.
        
        Returns:
            Dictionary mapping tile type to list of polygons
        """
        result: Dict[str, List[Polygon]] = {}
        
        for row in self.grid:
            for cell in row:
                if not cell.is_collapsed or not cell.collapsed_tile:
                    continue
                    
                tile = cell.collapsed_tile
                tile_type = tile.properties.get('type', 'unknown')
                
                if tile_type not in result:
                    result[tile_type] = []
                    
                poly = self._cell_to_polygon(cell.row, cell.col)
                
                # Clip to boundary
                clipped = poly.intersection(self.boundary)
                if not clipped.is_empty:
                    if clipped.geom_type == 'Polygon':
                        result[tile_type].append(clipped)
                    elif clipped.geom_type == 'MultiPolygon':
                        result[tile_type].extend(list(clipped.geoms))
                        
        return result


def solve_wfc(
    boundary: Polygon,
    tile_set: str = "industrial",
    tile_size: float = 10.0,
    seed: Optional[int] = None
) -> Dict[str, List[Polygon]]:
    """Convenience function to run WFC.
    
    Args:
        boundary: Polygon to fill
        tile_set: 'industrial' or 'residential'
        tile_size: Size of each tile (m)
        seed: Random seed
        
    Returns:
        Dictionary of tile type to polygons
    """
    config = WFCConfig(
        tile_size=tile_size,
        tile_set=tile_set,
        seed=seed
    )
    
    solver = WFCSolver(boundary, config)
    solver.solve()
    
    return solver.get_result_polygons()
