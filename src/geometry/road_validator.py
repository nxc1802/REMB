"""
Road Connectivity Validator using A* Pathfinding
FIX #3: Validates if plots can reach road network

Academic Reference:
- Hart, P. E.; Nilsson, N. J.; Raphael, B. (1968). "A Formal Basis for the 
  Heuristic Determination of Minimum Cost Paths". IEEE Transactions on Systems 
  Science and Cybernetics.
"""
import heapq
import numpy as np
from typing import List, Tuple, Optional, Set, Dict
from shapely.geometry import Polygon, LineString, Point
import logging

logger = logging.getLogger(__name__)


class Node:
    """Represents a grid cell in A* search"""
    
    def __init__(self, position: Tuple[int, int], parent: Optional['Node'] = None):
        self.position = position
        self.parent = parent
        
        # A* costs
        self.g = 0      # Cost from start
        self.h = 0      # Heuristic to goal
        self.f = 0      # Total (g + h)
    
    def __lt__(self, other):
        """Comparison for priority queue"""
        return self.f < other.f
    
    def __eq__(self, other):
        """Equality check"""
        if not isinstance(other, Node):
            return False
        return self.position == other.position
    
    def __hash__(self):
        """Make hashable for set operations"""
        return hash(self.position)


class RoadConnectivityValidator:
    """
    Validates if plot can reach road network using A* pathfinding
    
    Features:
    - Grid-based A* pathfinding
    - Manhattan distance heuristic (admissible)
    - Configurable grid resolution
    - Support for diagonal movement
    
    Usage:
        validator = RoadConnectivityValidator(
            grid_size=(100, 100),
            road_cells=road_cell_set,
            cell_size=5.0  # 5m per cell
        )
        
        can_access = validator.can_reach_road(plot_position)
        path = validator.find_path(start, goal)
    """
    
    def __init__(
        self,
        grid_size: Tuple[int, int],
        road_cells: Set[Tuple[int, int]],
        cell_size: float = 1.0,
        allow_diagonal: bool = False
    ):
        """
        Args:
            grid_size: (width, height) of grid in cells
            road_cells: Set of grid positions containing roads
            cell_size: Physical size of each cell (meters)
            allow_diagonal: If True, allow diagonal movement
        """
        self.grid_size = grid_size
        self.road_cells = road_cells
        self.cell_size = cell_size
        self.allow_diagonal = allow_diagonal
        self._obstacle_cells: Set[Tuple[int, int]] = set()
        
        logger.info(f"RoadConnectivityValidator initialized: {grid_size}, {len(road_cells)} road cells")
    
    def set_obstacles(self, obstacle_cells: Set[Tuple[int, int]]):
        """Set cells that are obstacles (e.g., existing plots)"""
        self._obstacle_cells = obstacle_cells
    
    def _get_neighbors(self, position: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Get valid neighboring cells
        
        Returns:
        - Orthogonal neighbors: up, down, left, right
        - Diagonal neighbors (if enabled)
        """
        x, y = position
        neighbors = []
        
        # Orthogonal neighbors (4-connectivity)
        orthogonal = [
            (x+1, y),    # Right
            (x-1, y),    # Left
            (x, y+1),    # Up
            (x, y-1),    # Down
        ]
        
        for nx, ny in orthogonal:
            if 0 <= nx < self.grid_size[0] and 0 <= ny < self.grid_size[1]:
                if (nx, ny) not in self._obstacle_cells:
                    neighbors.append((nx, ny))
        
        # Diagonal neighbors (8-connectivity)
        if self.allow_diagonal:
            diagonal = [
                (x+1, y+1),  # Up-Right
                (x-1, y+1),  # Up-Left
                (x+1, y-1),  # Down-Right
                (x-1, y-1),  # Down-Left
            ]
            
            for nx, ny in diagonal:
                if 0 <= nx < self.grid_size[0] and 0 <= ny < self.grid_size[1]:
                    if (nx, ny) not in self._obstacle_cells:
                        neighbors.append((nx, ny))
        
        return neighbors
    
    def _heuristic(
        self,
        current: Tuple[int, int],
        goal: Tuple[int, int]
    ) -> float:
        """
        Heuristic function for A*
        
        Uses Manhattan distance (admissible for grid with orthogonal movement)
        
        Formula: h(n) = |x_current - x_goal| + |y_current - y_goal|
        
        Properties:
        - Admissible: Never overestimates true cost
        - Consistent: h(n) <= cost(n, n') + h(n')
        """
        dx = abs(current[0] - goal[0])
        dy = abs(current[1] - goal[1])
        
        if self.allow_diagonal:
            # Diagonal distance (Chebyshev + diagonal cost)
            return max(dx, dy) + (np.sqrt(2) - 1) * min(dx, dy)
        else:
            # Manhattan distance
            return dx + dy
    
    def _reconstruct_path(self, node: Node) -> List[Tuple[int, int]]:
        """Reconstruct path from start to node"""
        path = []
        current = node
        while current is not None:
            path.append(current.position)
            current = current.parent
        return path[::-1]  # Reverse to get start -> end
    
    def find_path(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int]
    ) -> Optional[List[Tuple[int, int]]]:
        """
        Find shortest path from start to goal using A*
        
        Algorithm:
        1. Initialize: open_set = {start}, closed_set = {}
        2. While open_set not empty:
            a. Current = node with lowest f value
            b. If current == goal: return path
            c. Move current to closed_set
            d. For each neighbor:
                - Calculate g, h, f
                - If in closed_set: skip
                - If not in open_set or new g better: add/update
        3. If open_set empty and goal not found: no path
        
        Args:
            start: Starting position (grid coordinates)
            goal: Goal position (grid coordinates)
            
        Returns:
            Path as list of positions, or None if no path
        """
        # Validate positions
        if not (0 <= start[0] < self.grid_size[0] and 0 <= start[1] < self.grid_size[1]):
            logger.warning(f"Start position {start} out of bounds")
            return None
        
        if not (0 <= goal[0] < self.grid_size[0] and 0 <= goal[1] < self.grid_size[1]):
            logger.warning(f"Goal position {goal} out of bounds")
            return None
        
        # Initialize
        start_node = Node(start)
        start_node.g = 0
        start_node.h = self._heuristic(start, goal)
        start_node.f = start_node.h
        
        # Priority queue (min-heap)
        open_set = [start_node]
        open_dict = {start: start_node}  # For O(1) lookup
        closed_set: Set[Tuple[int, int]] = set()
        
        while open_set:
            # Get node with lowest f score
            current = heapq.heappop(open_set)
            del open_dict[current.position]
            
            # Goal reached
            if current.position == goal:
                return self._reconstruct_path(current)
            
            # Add to closed set
            closed_set.add(current.position)
            
            # Check neighbors
            for neighbor_pos in self._get_neighbors(current.position):
                if neighbor_pos in closed_set:
                    continue
                
                # Calculate costs
                move_cost = 1.0 if not self.allow_diagonal else (
                    np.sqrt(2) if abs(neighbor_pos[0] - current.position[0]) + 
                    abs(neighbor_pos[1] - current.position[1]) == 2 else 1.0
                )
                
                g = current.g + move_cost
                h = self._heuristic(neighbor_pos, goal)
                f = g + h
                
                # Check if in open set
                if neighbor_pos in open_dict:
                    existing = open_dict[neighbor_pos]
                    if g < existing.g:
                        # Update with better path
                        existing.g = g
                        existing.h = h
                        existing.f = f
                        existing.parent = current
                else:
                    # Add new node
                    neighbor = Node(neighbor_pos, current)
                    neighbor.g = g
                    neighbor.h = h
                    neighbor.f = f
                    heapq.heappush(open_set, neighbor)
                    open_dict[neighbor_pos] = neighbor
        
        # No path found
        return None
    
    def can_reach_road(
        self, 
        plot_position: Tuple[int, int], 
        search_radius: int = 100
    ) -> bool:
        """
        Check if position can reach road network
        
        Args:
            plot_position: Position to check (grid coordinates)
            search_radius: Maximum search radius in cells
            
        Returns:
            True if plot can reach any road cell
        """
        if not self.road_cells:
            logger.warning("No road cells defined")
            return False
        
        # Find closest road cell
        closest_road = None
        closest_dist = float('inf')
        
        for road_pos in self.road_cells:
            dist = abs(plot_position[0] - road_pos[0]) + abs(plot_position[1] - road_pos[1])
            if dist < closest_dist and dist <= search_radius:
                closest_dist = dist
                closest_road = road_pos
        
        if closest_road is None:
            logger.debug(f"No road within {search_radius} cells of {plot_position}")
            return False
        
        # Try to find path
        path = self.find_path(plot_position, closest_road)
        return path is not None
    
    def validate_all_plots(
        self, 
        plot_positions: List[Tuple[int, int]]
    ) -> Dict[int, bool]:
        """
        Validate road access for all plots
        
        Args:
            plot_positions: List of plot positions (grid coordinates)
            
        Returns:
            Dict mapping plot index to accessibility status
        """
        results = {}
        for i, pos in enumerate(plot_positions):
            results[i] = self.can_reach_road(pos)
        
        accessible = sum(1 for v in results.values() if v)
        logger.info(f"Road access validation: {accessible}/{len(plot_positions)} plots accessible")
        
        return results


# =============================================================================
# Helper Functions for Grid Conversion
# =============================================================================

def continuous_to_grid(
    position: Tuple[float, float],
    boundary: Dict[str, float],
    grid_size: Tuple[int, int]
) -> Tuple[int, int]:
    """
    Convert continuous coordinates to grid coordinates
    
    Args:
        position: (x, y) in continuous space
        boundary: {'min_x', 'max_x', 'min_y', 'max_y'}
        grid_size: (width, height) of grid
        
    Returns:
        (gx, gy) grid coordinates
    """
    x_norm = (position[0] - boundary['min_x']) / (boundary['max_x'] - boundary['min_x'])
    y_norm = (position[1] - boundary['min_y']) / (boundary['max_y'] - boundary['min_y'])
    
    gx = int(x_norm * grid_size[0])
    gy = int(y_norm * grid_size[1])
    
    # Clamp to valid range
    gx = max(0, min(grid_size[0] - 1, gx))
    gy = max(0, min(grid_size[1] - 1, gy))
    
    return (gx, gy)


def roads_to_grid(
    roads: List[Dict],
    boundary: Dict[str, float],
    grid_size: Tuple[int, int]
) -> Set[Tuple[int, int]]:
    """
    Convert road segments to grid cells using Bresenham's line algorithm
    
    Args:
        roads: List of {'start': (x, y), 'end': (x, y)}
        boundary: Boundary dict
        grid_size: Grid dimensions
        
    Returns:
        Set of grid cells containing roads
    """
    road_cells = set()
    
    for road in roads:
        start = continuous_to_grid(road['start'], boundary, grid_size)
        end = continuous_to_grid(road['end'], boundary, grid_size)
        
        # Bresenham's line algorithm
        points = bresenham_line(start[0], start[1], end[0], end[1])
        road_cells.update(points)
    
    return road_cells


def bresenham_line(x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
    """
    Bresenham's line algorithm
    
    Generates all grid cells on a line from (x0, y0) to (x1, y1)
    
    Args:
        x0, y0: Start point
        x1, y1: End point
        
    Returns:
        List of grid cells on the line
    """
    points = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    
    while True:
        points.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    
    return points


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Define roads
    roads = [
        {'start': (0, 200), 'end': (500, 200)},   # Horizontal
        {'start': (250, 0), 'end': (250, 400)},   # Vertical
    ]
    
    boundary = {'min_x': 0, 'max_x': 500, 'min_y': 0, 'max_y': 400}
    grid_size = (100, 80)  # 5m per cell
    
    # Convert roads to grid
    road_cells = roads_to_grid(roads, boundary, grid_size)
    
    # Create validator
    validator = RoadConnectivityValidator(
        grid_size=grid_size,
        road_cells=road_cells,
        cell_size=5.0
    )
    
    # Test plot positions
    plot1 = continuous_to_grid((100, 100), boundary, grid_size)
    plot2 = continuous_to_grid((400, 350), boundary, grid_size)
    
    print(f"Plot 1 ({plot1}) can reach road: {validator.can_reach_road(plot1)}")
    print(f"Plot 2 ({plot2}) can reach road: {validator.can_reach_road(plot2)}")
    
    # Find path
    path = validator.find_path(plot1, (50, 40))  # To road at y=40 (200m in continuous)
    print(f"Path length: {len(path) if path else 'No path'} cells")
