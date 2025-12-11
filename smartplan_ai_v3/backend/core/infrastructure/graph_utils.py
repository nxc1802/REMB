"""Graph algorithms for infrastructure routing.

Uses NetworkX for MST and pathfinding algorithms.
"""

from typing import List, Tuple, Optional, Dict, Any
from shapely.geometry import Point, LineString, Polygon
import networkx as nx
import numpy as np
import logging

logger = logging.getLogger(__name__)


def minimum_spanning_tree(
    points: List[Tuple[float, float]],
    weights: Optional[Dict[Tuple[int, int], float]] = None
) -> List[Tuple[int, int]]:
    """Calculate Minimum Spanning Tree connecting all points.
    
    Uses Euclidean distance as edge weights by default.
    
    Args:
        points: List of (x, y) coordinates
        weights: Optional custom edge weights
        
    Returns:
        List of (i, j) index pairs representing MST edges
    """
    if len(points) < 2:
        return []
    
    # Build complete graph
    G = nx.Graph()
    
    for i, p1 in enumerate(points):
        G.add_node(i, pos=p1)
        for j, p2 in enumerate(points[i+1:], start=i+1):
            if weights and (i, j) in weights:
                weight = weights[(i, j)]
            else:
                # Euclidean distance
                weight = np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
            G.add_edge(i, j, weight=weight)
    
    # Calculate MST using Kruskal's algorithm
    mst = nx.minimum_spanning_tree(G, weight='weight')
    
    return list(mst.edges())


def points_to_linestrings(
    points: List[Tuple[float, float]],
    edges: List[Tuple[int, int]]
) -> List[LineString]:
    """Convert MST edges to LineString geometries.
    
    Args:
        points: List of point coordinates
        edges: List of (i, j) edge indices
        
    Returns:
        List of Shapely LineStrings
    """
    lines = []
    for i, j in edges:
        if 0 <= i < len(points) and 0 <= j < len(points):
            lines.append(LineString([points[i], points[j]]))
    return lines


def build_visibility_graph(
    points: List[Tuple[float, float]],
    obstacles: List[Polygon]
) -> nx.Graph:
    """Build visibility graph for pathfinding with obstacles.
    
    Edges exist between points if the line of sight is not blocked.
    
    Args:
        points: List of point coordinates
        obstacles: List of obstacle polygons
        
    Returns:
        NetworkX graph with visible edges
    """
    G = nx.Graph()
    
    for i, p1 in enumerate(points):
        G.add_node(i, pos=p1)
        
        for j, p2 in enumerate(points[i+1:], start=i+1):
            line = LineString([p1, p2])
            
            # Check if line intersects any obstacle
            blocked = False
            for obstacle in obstacles:
                if line.intersects(obstacle) and not line.touches(obstacle):
                    blocked = True
                    break
            
            if not blocked:
                distance = np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
                G.add_edge(i, j, weight=distance)
    
    return G


def steiner_tree_approximation(
    terminal_points: List[Tuple[float, float]],
    grid_points: List[Tuple[float, float]] = None,
    obstacles: List[Polygon] = None
) -> List[Tuple[int, int]]:
    """Approximate Steiner Tree using MST heuristic.
    
    Steiner tree allows additional points (Steiner points) to reduce
    total edge length. This uses MST as approximation.
    
    Args:
        terminal_points: Required points to connect
        grid_points: Optional additional Steiner point candidates
        obstacles: Optional obstacles to avoid
        
    Returns:
        List of edge indices
    """
    if not terminal_points:
        return []
    
    # Combine terminal and grid points
    all_points = list(terminal_points)
    terminal_count = len(terminal_points)
    
    if grid_points:
        all_points.extend(grid_points)
    
    # Build graph (with obstacle avoidance if needed)
    if obstacles:
        G = build_visibility_graph(all_points, obstacles)
    else:
        # Build complete graph
        G = nx.Graph()
        for i, p1 in enumerate(all_points):
            for j, p2 in enumerate(all_points[i+1:], start=i+1):
                dist = np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
                G.add_edge(i, j, weight=dist)
    
    # Calculate MST
    try:
        mst = nx.minimum_spanning_tree(G, weight='weight')
        return list(mst.edges())
    except nx.NetworkXError:
        # Graph might be disconnected
        logger.warning("Graph is disconnected, using MST on terminal points only")
        return minimum_spanning_tree(terminal_points)


def shortest_path(
    graph: nx.Graph,
    source: int,
    target: int
) -> List[int]:
    """Find shortest path between two nodes.
    
    Args:
        graph: NetworkX graph
        source: Source node index
        target: Target node index
        
    Returns:
        List of node indices in path
    """
    try:
        return nx.shortest_path(graph, source, target, weight='weight')
    except nx.NetworkXNoPath:
        return []


def connect_to_edge(
    point: Tuple[float, float],
    boundary: Polygon,
    existing_lines: List[LineString] = None
) -> Optional[LineString]:
    """Connect a point to the nearest boundary edge.
    
    Useful for connecting utilities to road network.
    
    Args:
        point: Point to connect
        boundary: Boundary polygon (represents road network edge)
        existing_lines: Optional lines to avoid crossing
        
    Returns:
        LineString connecting point to boundary, or None
    """
    if boundary is None or boundary.is_empty:
        return None
    
    p = Point(point)
    
    # Find nearest point on boundary
    nearest = boundary.exterior.interpolate(boundary.exterior.project(p))
    
    line = LineString([point, (nearest.x, nearest.y)])
    
    # Check for crossings with existing lines
    if existing_lines:
        for existing in existing_lines:
            if line.crosses(existing):
                # Simple case: just return the line anyway
                # More complex routing would need pathfinding
                pass
    
    return line
