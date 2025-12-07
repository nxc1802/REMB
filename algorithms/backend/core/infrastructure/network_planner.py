"""
Electrical network planning using MST with loop redundancy.

Creates a minimum spanning tree network between lots, then adds
redundant edges for reliability (loop network).
"""

import logging
from typing import List, Tuple

import numpy as np
import networkx as nx
from shapely.geometry import Polygon, LineString

from core.config.settings import InfrastructureSettings, DEFAULT_SETTINGS

logger = logging.getLogger(__name__)


def generate_loop_network(
    lots: List[Polygon],
    max_distance: float = None,
    redundancy_ratio: float = None
) -> Tuple[List[List[float]], List[LineString]]:
    """
    Generate Loop Network for electrical/utility infrastructure.
    
    Creates MST (Minimum Spanning Tree) then adds back 15% of edges
    for redundancy/safety (loop network pattern).
    
    Args:
        lots: List of lot polygons
        max_distance: Maximum connection distance (m)
        redundancy_ratio: Extra edges to add (0.0-1.0)
        
    Returns:
        (points, connection_lines) where:
        - points: List of [x, y] coordinates
        - connection_lines: List of LineString connections
    """
    settings = DEFAULT_SETTINGS.infrastructure
    max_dist = max_distance or settings.max_connection_distance
    redundancy = redundancy_ratio or settings.loop_redundancy_ratio
    
    if len(lots) < 2:
        logger.warning("Need at least 2 lots for network generation")
        return [], []
    
    # Get lot centroids
    centroids = [lot.centroid for lot in lots]
    points = [[p.x, p.y] for p in centroids]
    
    # Build full graph with nearby connections
    G = nx.Graph()
    for i, p in enumerate(centroids):
        G.add_node(i, pos=(p.x, p.y))
    
    # Add edges for all pairs within max distance
    for i in range(len(centroids)):
        for j in range(i + 1, len(centroids)):
            dist = centroids[i].distance(centroids[j])
            if dist < max_dist:
                G.add_edge(i, j, weight=dist)
    
    # Handle disconnected graph
    if not nx.is_connected(G):
        components = list(nx.connected_components(G))
        largest_comp = max(components, key=len)
        G = G.subgraph(largest_comp).copy()
        logger.warning(f"Graph disconnected, using largest component ({len(largest_comp)} nodes)")
    
    if G.number_of_edges() == 0:
        logger.warning("No edges in graph")
        return points, []
    
    # Create Minimum Spanning Tree
    mst = nx.minimum_spanning_tree(G)
    
    # Create Loop: Add back redundant edges for safety
    all_edges = sorted(G.edges(data=True), key=lambda x: x[2]['weight'])
    loop_graph = mst.copy()
    
    target_extra = int(len(lots) * redundancy)
    added_count = 0
    
    for u, v, data in all_edges:
        if not loop_graph.has_edge(u, v):
            loop_graph.add_edge(u, v, **data)
            added_count += 1
            if added_count >= target_extra:
                break
    
    # Convert to LineStrings
    connections = []
    for u, v in loop_graph.edges():
        if u < len(centroids) and v < len(centroids):
            connections.append(LineString([centroids[u], centroids[v]]))
    
    logger.debug(f"Generated network: {len(connections)} connections, {added_count} redundant")
    return points, connections
