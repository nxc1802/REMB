"""
Shape quality analysis for aesthetic optimization.

Implements geometric quality metrics from Beauti_mode.md:
- Rectangularity (area / OBB area)
- Aspect Ratio (length / width)
- Minimum area constraints

Used to filter poor-quality lots and convert them to green spaces.
"""

import numpy as np
from shapely.geometry import Polygon
from typing import Tuple, Optional


# Default thresholds from Beauti_mode.md
DEFAULT_MIN_RECTANGULARITY = 0.75
DEFAULT_MAX_ASPECT_RATIO = 4.0
DEFAULT_MIN_LOT_AREA = 1000.0  # m²


def analyze_shape_quality(
    polygon: Polygon,
    min_rectangularity: float = DEFAULT_MIN_RECTANGULARITY,
    max_aspect_ratio: float = DEFAULT_MAX_ASPECT_RATIO,
    min_area: float = DEFAULT_MIN_LOT_AREA
) -> Tuple[float, bool]:
    """
    Analyze shape quality and return aesthetic score with validity status.
    
    Uses Oriented Bounding Box (OBB) to calculate metrics:
    - Rectangularity: ratio of polygon area to its OBB area
    - Aspect Ratio: ratio of OBB length to width
    
    Args:
        polygon: Shapely Polygon to analyze
        min_rectangularity: Minimum acceptable rectangularity (0-1)
        max_aspect_ratio: Maximum acceptable length/width ratio
        min_area: Minimum acceptable lot area (m²)
        
    Returns:
        (score, is_valid) tuple where:
        - score: Aesthetic score between 0 and 1 (higher = better)
        - is_valid: True if lot meets all quality thresholds
    """
    if polygon.is_empty or not polygon.is_valid:
        return 0.0, False
    
    # Calculate OBB (Oriented Bounding Box)
    obb = polygon.minimum_rotated_rectangle
    
    if obb.is_empty or obb.area <= 0:
        return 0.0, False
    
    # Rectangularity: how well the polygon fills its OBB
    # Perfect rectangle = 1.0, Triangle ≈ 0.5
    rectangularity = polygon.area / obb.area
    
    # Calculate aspect ratio from OBB edges
    x, y = obb.exterior.coords.xy
    
    # Get two adjacent edges of OBB
    edge_1 = np.hypot(x[1] - x[0], y[1] - y[0])
    edge_2 = np.hypot(x[2] - x[1], y[2] - y[1])
    
    if edge_1 == 0 or edge_2 == 0:
        return 0.0, False
    
    # Aspect ratio: longer edge / shorter edge
    width, length = sorted([edge_1, edge_2])
    aspect_ratio = length / width
    
    # --- HARD CONSTRAINTS ---
    is_valid = True
    
    # Rule 1: Must be reasonably rectangular
    if rectangularity < min_rectangularity:
        is_valid = False
    
    # Rule 2: Cannot be too elongated
    if aspect_ratio > max_aspect_ratio:
        is_valid = False
    
    # Rule 3: Minimum area to avoid tiny fragments
    if polygon.area < min_area:
        is_valid = False
    
    # Calculate aesthetic score (for optimization objective)
    # Higher rectangularity and lower aspect ratio = higher score
    score = (rectangularity * 0.7) + ((1.0 / aspect_ratio) * 0.3)
    
    return score, is_valid


def get_dominant_edge_vector(polygon: Polygon) -> Optional[np.ndarray]:
    """
    Find the unit vector of the longest edge (typically the frontage).
    
    Used for orthogonal alignment - lots should be cut perpendicular
    to this dominant direction.
    
    Args:
        polygon: Shapely Polygon to analyze
        
    Returns:
        Unit vector (2D numpy array) of the longest edge,
        or None if polygon is invalid
    """
    if polygon.is_empty or not polygon.is_valid:
        return None
    
    # Use OBB to find dominant direction
    rect = polygon.minimum_rotated_rectangle
    x, y = rect.exterior.coords.xy
    
    # Get first 3 points to find 2 adjacent edges
    p0 = np.array([x[0], y[0]])
    p1 = np.array([x[1], y[1]])
    p2 = np.array([x[2], y[2]])
    
    edge1_len = np.linalg.norm(p1 - p0)
    edge2_len = np.linalg.norm(p2 - p1)
    
    # Select longer edge
    if edge1_len > edge2_len:
        vec = p1 - p0
    else:
        vec = p2 - p1
    
    # Return unit vector
    norm = np.linalg.norm(vec)
    if norm == 0:
        return None
    
    return vec / norm


def get_perpendicular_vector(vector: np.ndarray) -> np.ndarray:
    """
    Get perpendicular vector (90 degree rotation).
    
    Args:
        vector: 2D numpy array
        
    Returns:
        Perpendicular unit vector
    """
    return np.array([-vector[1], vector[0]])


def get_obb_dimensions(polygon: Polygon) -> Tuple[float, float, float]:
    """
    Get oriented bounding box dimensions.
    
    Args:
        polygon: Shapely Polygon
        
    Returns:
        (width, length, angle_degrees) where width <= length
    """
    if polygon.is_empty or not polygon.is_valid:
        return 0.0, 0.0, 0.0
    
    obb = polygon.minimum_rotated_rectangle
    x, y = obb.exterior.coords.xy
    
    # Calculate edges
    edge_1 = np.hypot(x[1] - x[0], y[1] - y[0])
    edge_2 = np.hypot(x[2] - x[1], y[2] - y[1])
    
    width, length = sorted([edge_1, edge_2])
    
    # Calculate rotation angle of longer edge
    if edge_1 > edge_2:
        dx, dy = x[1] - x[0], y[1] - y[0]
    else:
        dx, dy = x[2] - x[1], y[2] - y[1]
    
    angle_rad = np.arctan2(dy, dx)
    angle_deg = np.degrees(angle_rad)
    
    return width, length, angle_deg


def classify_lot_type(
    polygon: Polygon,
    min_rectangularity: float = DEFAULT_MIN_RECTANGULARITY,
    max_aspect_ratio: float = DEFAULT_MAX_ASPECT_RATIO,
    min_area: float = DEFAULT_MIN_LOT_AREA
) -> str:
    """
    Classify lot into categories based on shape quality.
    
    Args:
        polygon: Lot polygon to classify
        min_rectangularity: Threshold for commercial use
        max_aspect_ratio: Threshold for commercial use
        min_area: Minimum area for any use
        
    Returns:
        Classification string:
        - 'commercial': Good shape, suitable for industrial/commercial
        - 'green_space': Poor shape, should be converted to park/utility
        - 'unusable': Too small or invalid
    """
    if polygon.is_empty or not polygon.is_valid:
        return 'unusable'
    
    if polygon.area < min_area:
        return 'unusable'
    
    score, is_valid = analyze_shape_quality(
        polygon, min_rectangularity, max_aspect_ratio, min_area
    )
    
    if is_valid:
        return 'commercial'
    else:
        return 'green_space'
