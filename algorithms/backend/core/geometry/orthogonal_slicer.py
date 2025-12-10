"""
Orthogonal slicing for regular lot subdivision.

Implements orthogonal alignment from Beauti_mode.md:
- Cuts perpendicular to dominant edge (usually frontage)
- Creates parallel, regular lot shapes
- Uses coordinate rotation for clean geometry

Forces 90-degree cutting angles for professional-looking layouts.
"""

import numpy as np
from shapely.geometry import Polygon, LineString, box
from shapely.affinity import rotate, translate
from shapely.ops import split
from typing import List, Optional, Tuple

from core.geometry.shape_quality import (
    get_dominant_edge_vector,
    get_perpendicular_vector,
    get_obb_dimensions
)


def orthogonal_slice(
    block: Polygon,
    lot_widths: List[float],
    buffer_distance: float = 0.1
) -> List[Polygon]:
    """
    Slice block into lots perpendicular to its dominant edge.
    
    This creates regular, parallel lots aligned to the block's
    natural orientation (typically road frontage).
    
    Args:
        block: Block polygon to subdivide
        lot_widths: List of widths for each lot
        buffer_distance: Small buffer to ensure clean cuts
        
    Returns:
        List of lot polygons
    """
    if block.is_empty or not block.is_valid:
        return []
    
    if not lot_widths:
        return [block]
    
    # Get dominant direction vector
    direction_vec = get_dominant_edge_vector(block)
    if direction_vec is None:
        # Fallback to axis-aligned slicing
        return _axis_aligned_slice(block, lot_widths)
    
    # Get perpendicular vector for cutting
    perp_vec = get_perpendicular_vector(direction_vec)
    
    # Calculate rotation angle to align with X-axis
    angle_rad = np.arctan2(direction_vec[1], direction_vec[0])
    angle_deg = np.degrees(angle_rad)
    
    # Rotate block to align dominant edge with X-axis
    center = block.centroid
    rotated_block = rotate(block, -angle_deg, origin=center)
    
    # Perform axis-aligned slicing on rotated block
    rotated_lots = _axis_aligned_slice(rotated_block, lot_widths)
    
    # Rotate lots back to original orientation
    lots = [rotate(lot, angle_deg, origin=center) for lot in rotated_lots]
    
    # Clip to original block boundary (handles edge cases)
    clipped_lots = []
    for lot in lots:
        clipped = lot.intersection(block)
        if not clipped.is_empty and clipped.geom_type == 'Polygon':
            clipped_lots.append(clipped)
    
    return clipped_lots


def _axis_aligned_slice(
    block: Polygon,
    lot_widths: List[float]
) -> List[Polygon]:
    """
    Slice block along X-axis (assumes block is axis-aligned).
    
    Args:
        block: Block polygon to subdivide
        lot_widths: List of widths for each lot
        
    Returns:
        List of lot polygons
    """
    minx, miny, maxx, maxy = block.bounds
    total_width = maxx - minx
    block_height = maxy - miny
    
    # Scale widths to fit block if necessary
    sum_widths = sum(lot_widths)
    if sum_widths > 0:
        scale_factor = total_width / sum_widths
        scaled_widths = [w * scale_factor for w in lot_widths]
    else:
        return [block]
    
    lots = []
    current_x = minx
    
    for width in scaled_widths:
        # Create rectangular lot
        lot_poly = box(current_x, miny, current_x + width, maxy)
        
        # Clip to block boundary
        clipped = lot_poly.intersection(block)
        if not clipped.is_empty and clipped.geom_type == 'Polygon':
            lots.append(clipped)
        
        current_x += width
    
    return lots


def slice_along_direction(
    block: Polygon,
    direction_vec: np.ndarray,
    num_slices: int,
    target_width: Optional[float] = None
) -> List[Polygon]:
    """
    Slice block along a specific direction vector.
    
    Args:
        block: Block polygon to subdivide
        direction_vec: Unit vector for slice direction
        num_slices: Number of slices to create
        target_width: Optional target width (overrides num_slices)
        
    Returns:
        List of lot polygons
    """
    if block.is_empty or not block.is_valid:
        return []
    
    if num_slices <= 0:
        return [block]
    
    # Get OBB dimensions
    width, length, _ = get_obb_dimensions(block)
    
    # Calculate widths
    if target_width and target_width > 0:
        num_slices = max(1, int(length / target_width))
    
    slice_width = length / num_slices if num_slices > 0 else length
    lot_widths = [slice_width] * num_slices
    
    return orthogonal_slice(block, lot_widths)


def create_cutting_lines(
    block: Polygon,
    num_cuts: int,
    direction_vec: Optional[np.ndarray] = None
) -> List[LineString]:
    """
    Create cutting lines for visualization or debugging.
    
    Args:
        block: Block polygon
        num_cuts: Number of cutting lines
        direction_vec: Optional direction vector (uses dominant if None)
        
    Returns:
        List of LineString cutting lines
    """
    if block.is_empty or not block.is_valid:
        return []
    
    if direction_vec is None:
        direction_vec = get_dominant_edge_vector(block)
        if direction_vec is None:
            return []
    
    perp_vec = get_perpendicular_vector(direction_vec)
    
    # Get block bounds and diagonal
    minx, miny, maxx, maxy = block.bounds
    diagonal = np.hypot(maxx - minx, maxy - miny)
    
    # Get OBB dimensions for spacing
    width, length, _ = get_obb_dimensions(block)
    spacing = length / (num_cuts + 1) if num_cuts > 0 else length
    
    center = np.array([block.centroid.x, block.centroid.y])
    
    cutting_lines = []
    
    for i in range(1, num_cuts + 1):
        # Calculate offset from center
        offset = (i - (num_cuts + 1) / 2) * spacing
        
        # Line center point
        line_center = center + direction_vec * offset
        
        # Create line extending perpendicular to direction
        p1 = line_center - perp_vec * diagonal
        p2 = line_center + perp_vec * diagonal
        
        line = LineString([p1, p2])
        cutting_lines.append(line)
    
    return cutting_lines


def subdivide_with_uniform_widths(
    block: Polygon,
    target_width: float = 40.0,
    min_width: float = 20.0,
    max_width: float = 80.0
) -> Tuple[List[Polygon], List[float]]:
    """
    Subdivide block with uniform lot widths.
    
    Calculates optimal number of lots to match target width
    while respecting min/max constraints.
    
    Args:
        block: Block polygon to subdivide
        target_width: Target lot width (m)
        min_width: Minimum acceptable width (m)
        max_width: Maximum acceptable width (m)
        
    Returns:
        (lots, widths) tuple
    """
    if block.is_empty or not block.is_valid:
        return [], []
    
    # Get OBB dimensions
    width, length, _ = get_obb_dimensions(block)
    
    # Calculate optimal number of lots
    num_lots = max(1, round(length / target_width))
    
    # Calculate actual width
    actual_width = length / num_lots
    
    # Adjust if outside bounds
    if actual_width < min_width:
        num_lots = max(1, int(length / min_width))
        actual_width = length / num_lots
    elif actual_width > max_width:
        num_lots = max(1, int(length / max_width) + 1)
        actual_width = length / num_lots
    
    lot_widths = [actual_width] * num_lots
    
    lots = orthogonal_slice(block, lot_widths)
    
    return lots, lot_widths
