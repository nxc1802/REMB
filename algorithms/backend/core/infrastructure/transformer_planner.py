"""
Transformer station placement using K-Means clustering.

Optimally positions electrical transformer stations to serve
lots within a defined service radius.
"""

import logging
from typing import List, Tuple, Optional

import numpy as np
from sklearn.cluster import KMeans
from shapely.geometry import Polygon

from core.config.settings import InfrastructureSettings, DEFAULT_SETTINGS

logger = logging.getLogger(__name__)


def generate_transformers(
    lots: List[Polygon],
    lots_per_transformer: Optional[int] = None,
    service_radius: Optional[float] = None
) -> List[Tuple[float, float]]:
    """
    Cluster lots to determine optimal transformer placements.
    
    Uses K-Means clustering with dynamic k based on lot count.
    
    Args:
        lots: List of lot polygons
        lots_per_transformer: Approximate lots per transformer
        service_radius: Service radius (for reference, not used in clustering)
        
    Returns:
        List of (x, y) transformer locations
    """
    settings = DEFAULT_SETTINGS.infrastructure
    lots_per_tf = lots_per_transformer or settings.lots_per_transformer
    
    if not lots:
        return []
    
    if len(lots) == 1:
        # Single lot - transformer at centroid
        c = lots[0].centroid
        return [(c.x, c.y)]
    
    # Get lot centroids
    lot_coords = np.array([
        [lot.centroid.x, lot.centroid.y] 
        for lot in lots
    ])
    
    # Calculate number of transformers
    num_transformers = max(1, len(lots) // lots_per_tf)
    
    # Don't exceed number of lots
    num_transformers = min(num_transformers, len(lots))
    
    # K-Means clustering
    try:
        kmeans = KMeans(
            n_clusters=num_transformers, 
            n_init=10,
            random_state=42
        )
        kmeans.fit(lot_coords)
        
        centers = [tuple(c) for c in kmeans.cluster_centers_]
        logger.debug(f"Placed {len(centers)} transformers for {len(lots)} lots")
        return centers
        
    except Exception as e:
        logger.error(f"K-Means clustering failed: {e}")
        # Fallback: centroid of all lots
        mean_x = np.mean(lot_coords[:, 0])
        mean_y = np.mean(lot_coords[:, 1])
        return [(mean_x, mean_y)]
