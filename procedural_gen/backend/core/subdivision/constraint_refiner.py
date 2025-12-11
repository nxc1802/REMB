"""Constraint-based lot refinement using OR-Tools.

Integrates with the existing algorithms/ OR-Tools solver
for fine-tuning lot dimensions to meet exact constraints.

Reference: Implementation Plan v2 - Hybrid Architecture
"""

from typing import List, Optional, Tuple
import logging
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union

logger = logging.getLogger(__name__)

# Try to import OR-Tools
try:
    from ortools.sat.python import cp_model
    HAS_ORTOOLS = True
except ImportError:
    HAS_ORTOOLS = False
    logger.warning("OR-Tools not available, using heuristic refinement")


class ConstraintRefiner:
    """Refine lots using constraint programming.
    
    Uses OR-Tools CP-SAT solver to adjust lot widths for
    optimal packing. This is a simplified version of the
    SubdivisionSolver from algorithms/ project.
    
    Constraints:
    - Sum of lot widths = block length
    - Each lot width in [min_width, max_width]
    - Minimize deviation from target width
    """
    
    def __init__(
        self,
        min_width: float = 20.0,
        max_width: float = 80.0,
        target_width: float = 40.0,
        time_limit: float = 5.0
    ):
        """Initialize constraint refiner.
        
        Args:
            min_width: Minimum lot width (m)
            max_width: Maximum lot width (m)
            target_width: Target lot width (m)
            time_limit: Solver time limit (seconds)
        """
        self.min_width = min_width
        self.max_width = max_width
        self.target_width = target_width
        self.time_limit = time_limit
        
    def refine_lot_widths(
        self,
        total_length: float,
        num_lots: int
    ) -> List[float]:
        """Compute optimal lot widths for a block.
        
        Args:
            total_length: Total length to subdivide (m)
            num_lots: Number of lots to create
            
        Returns:
            List of lot widths
        """
        if not HAS_ORTOOLS:
            return self._heuristic_widths(total_length, num_lots)
            
        return self._ortools_widths(total_length, num_lots)
        
    def refine_lots_in_block(
        self,
        block: Polygon,
        direction: Optional[LineString] = None
    ) -> List[Polygon]:
        """Refine lot subdivision in a block.
        
        Uses constraint solver to determine optimal lot widths,
        then slices block accordingly.
        
        Args:
            block: Block polygon to subdivide
            direction: Optional direction for slicing
            
        Returns:
            List of refined lot polygons
        """
        from core.geometry import get_obb_dimensions, get_dominant_edge_vector
        
        # Get block dimensions
        width, length, angle = get_obb_dimensions(block)
        
        if length < self.min_width * 2:
            return [block]  # Too small to subdivide
            
        # Calculate number of lots
        num_lots = max(1, int(length / self.target_width))
        
        # Get optimal widths
        widths = self.refine_lot_widths(length, num_lots)
        
        if not widths:
            return [block]
            
        # Slice block using widths
        lots = self._slice_block(block, widths, angle)
        
        return lots
        
    def _ortools_widths(
        self, 
        total_length: float, 
        num_lots: int
    ) -> List[float]:
        """Compute widths using OR-Tools solver.
        
        Args:
            total_length: Total length (m)
            num_lots: Number of lots
            
        Returns:
            Optimal lot widths
        """
        # Scale to integers (centimeters)
        scale = 100
        total_cm = int(total_length * scale)
        min_cm = int(self.min_width * scale)
        max_cm = int(self.max_width * scale)
        target_cm = int(self.target_width * scale)
        
        model = cp_model.CpModel()
        
        # Variables: width of each lot
        widths = [
            model.NewIntVar(min_cm, max_cm, f"width_{i}")
            for i in range(num_lots)
        ]
        
        # Constraint: sum equals total
        model.Add(sum(widths) == total_cm)
        
        # Objective: minimize deviation from target
        deviations = []
        for w in widths:
            dev_pos = model.NewIntVar(0, max_cm, "")
            dev_neg = model.NewIntVar(0, max_cm, "")
            model.Add(w - target_cm == dev_pos - dev_neg)
            deviations.append(dev_pos + dev_neg)
            
        model.Minimize(sum(deviations))
        
        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit
        
        status = solver.Solve(model)
        
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return [solver.Value(w) / scale for w in widths]
        else:
            logger.warning("OR-Tools solver failed, using heuristic")
            return self._heuristic_widths(total_length, num_lots)
            
    def _heuristic_widths(
        self, 
        total_length: float, 
        num_lots: int
    ) -> List[float]:
        """Compute widths using simple heuristic.
        
        Args:
            total_length: Total length (m)
            num_lots: Number of lots
            
        Returns:
            List of lot widths
        """
        if num_lots <= 0:
            return []
            
        # Start with equal division
        base_width = total_length / num_lots
        
        # Clamp to bounds
        clamped_width = max(self.min_width, min(self.max_width, base_width))
        
        # Adjust number if needed
        if clamped_width > base_width:
            # Widths too large - reduce lot count
            num_lots = max(1, int(total_length / clamped_width))
            base_width = total_length / num_lots
            
        # Create slightly varied widths to total exactly
        widths = [base_width] * (num_lots - 1)
        widths.append(total_length - sum(widths))  # Last one gets remainder
        
        return widths
        
    def _slice_block(
        self,
        block: Polygon,
        widths: List[float],
        angle: float
    ) -> List[Polygon]:
        """Slice block into lots using computed widths.
        
        Args:
            block: Block polygon
            widths: List of lot widths
            angle: Slicing angle (degrees)
            
        Returns:
            List of lot polygons
        """
        import numpy as np
        from core.geometry import get_dominant_edge_vector
        
        lots = []
        
        # Get OBB
        obb = block.minimum_rotated_rectangle
        center = obb.centroid
        
        # Compute slicing direction
        angle_rad = np.radians(angle)
        direction = np.array([np.cos(angle_rad), np.sin(angle_rad)])
        perp = np.array([-direction[1], direction[0]])
        
        # Get starting point
        minx, miny, maxx, maxy = block.bounds
        diagonal = np.hypot(maxx - minx, maxy - miny)
        
        # Start from one edge
        start_point = center.x - direction[0] * diagonal / 2
        start_y = center.y - direction[1] * diagonal / 2
        
        current_pos = 0
        remaining = block
        
        for width in widths[:-1]:
            current_pos += width
            
            # Create cutting line
            cut_x = start_point + direction[0] * current_pos
            cut_y = start_y + direction[1] * current_pos
            
            cut_line = LineString([
                (cut_x - perp[0] * diagonal, cut_y - perp[1] * diagonal),
                (cut_x + perp[0] * diagonal, cut_y + perp[1] * diagonal)
            ])
            
            # Split remaining polygon
            try:
                from shapely.ops import split
                parts = split(remaining, cut_line)
                
                if len(parts.geoms) >= 2:
                    # Take first part as lot
                    lot = parts.geoms[0]
                    if lot.geom_type == 'Polygon' and not lot.is_empty:
                        lots.append(lot)
                    
                    # Remaining becomes rest
                    remaining = unary_union(parts.geoms[1:])
                    if remaining.geom_type == 'MultiPolygon':
                        remaining = max(remaining.geoms, key=lambda g: g.area)
            except Exception as e:
                logger.warning(f"Slice failed: {e}")
                break
                
        # Add remaining as last lot
        if remaining.geom_type == 'Polygon' and not remaining.is_empty:
            lots.append(remaining)
            
        return lots


def refine_subdivision(
    lots: List[Polygon],
    target_width: float = 40.0,
    min_width: float = 20.0,
    max_width: float = 80.0
) -> List[Polygon]:
    """Convenience function to refine lot dimensions.
    
    Args:
        lots: Input lots (may be from OBB Tree)
        target_width: Target lot width (m)
        min_width: Minimum width (m)
        max_width: Maximum width (m)
        
    Returns:
        Refined lots
    """
    refiner = ConstraintRefiner(
        min_width=min_width,
        max_width=max_width,
        target_width=target_width
    )
    
    refined = []
    
    for lot in lots:
        if lot.is_empty:
            continue
            
        # Only refine if lot is large enough
        if lot.area > target_width * target_width * 4:
            sub_lots = refiner.refine_lots_in_block(lot)
            refined.extend(sub_lots)
        else:
            refined.append(lot)
            
    return refined
