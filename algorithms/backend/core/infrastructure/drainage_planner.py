"""
Drainage flow planning for gravity-based wastewater systems.

Calculates flow directions from each lot towards the
Wastewater Treatment Plant (WWTP/XLNT) located at the lowest elevation.
"""

import logging
import math
from typing import List, Dict, Any, Optional

from shapely.geometry import Polygon, Point

from core.config.settings import InfrastructureSettings, DEFAULT_SETTINGS

logger = logging.getLogger(__name__)


def calculate_drainage(
    lots: List[Polygon],
    wwtp_centroid: Optional[Point],
    arrow_length: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Calculate drainage flow direction towards WWTP (gravity flow).
    
    Creates directional arrows from each lot centroid pointing
    towards the wastewater treatment plant.
    
    Args:
        lots: List of lot polygons
        wwtp_centroid: Location of WWTP (lowest elevation)
        arrow_length: Visualization arrow length (m)
        
    Returns:
        List of dicts with 'start' and 'vector' keys
    """
    settings = DEFAULT_SETTINGS.infrastructure
    arrow_len = arrow_length or settings.drainage_arrow_length
    
    arrows = []
    
    if not wwtp_centroid:
        logger.warning("No WWTP location provided, skipping drainage calculation")
        return arrows
    
    if not lots:
        return arrows
    
    for lot in lots:
        try:
            c = lot.centroid
            
            # Vector from lot to WWTP
            dx = wwtp_centroid.x - c.x
            dy = wwtp_centroid.y - c.y
            
            # Calculate length (with safe division)
            length = math.sqrt(dx * dx + dy * dy)
            
            if length > 0:
                # Normalize vector and scale to arrow length
                norm_dx = dx / length * arrow_len
                norm_dy = dy / length * arrow_len
                
                arrows.append({
                    'start': (c.x, c.y),
                    'vector': (norm_dx, norm_dy)
                })
            else:
                # Lot is at WWTP location (unlikely but handle it)
                logger.debug("Lot centroid coincides with WWTP")
                
        except Exception as e:
            logger.warning(f"Error calculating drainage for lot: {e}")
            continue
    
    logger.debug(f"Calculated drainage for {len(arrows)} lots")
    return arrows
