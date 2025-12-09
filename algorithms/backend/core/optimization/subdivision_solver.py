"""
Block subdivision solver using OR-Tools constraint programming.

Optimizes lot widths within blocks to meet target dimensions while
respecting minimum/maximum constraints.
"""

import logging
from typing import List, Dict, Any, Optional

import numpy as np
from shapely.geometry import Polygon
from ortools.sat.python import cp_model

from core.config.settings import (
    SubdivisionSettings, 
    DEFAULT_SETTINGS,
    DEVIATION_PENALTY_WEIGHT,
)
from core.geometry.orthogonal_slicer import orthogonal_slice
from core.geometry.shape_quality import get_obb_dimensions

logger = logging.getLogger(__name__)


class SubdivisionSolver:
    """
    Stage 2: Optimize block subdivision using OR-Tools CP-SAT solver.
    
    Solves for optimal lot widths that:
    - Sum to total available length
    - Stay within min/max bounds
    - Minimize deviation from target width
    """
    
    @staticmethod
    def solve_subdivision(
        total_length: float, 
        min_width: float, 
        max_width: float, 
        target_width: float, 
        time_limit: float = 5.0,
        deviation_penalty_weight: float = DEVIATION_PENALTY_WEIGHT
    ) -> List[float]:
        """
        Solve optimal lot widths using constraint programming.
        
        Uses weighted objective from Beauti_mode.md:
        Maximize(sum(widths) * 100 - sum(deviations) * penalty_weight)
        
        Args:
            total_length: Total length to subdivide
            min_width: Minimum lot width
            max_width: Maximum lot width
            target_width: Target lot width
            time_limit: Solver time limit in seconds
            deviation_penalty_weight: Weight for deviation penalty (higher = more uniform)
            
        Returns:
            List of lot widths
        """
        # Input validation
        if total_length <= 0:
            logger.warning("Total length must be positive")
            return []
        if min_width <= 0:
            logger.warning("Minimum width must be positive")
            return []
        if total_length < min_width:
            logger.warning(f"Total length ({total_length}) < min width ({min_width})")
            return []
        if min_width > max_width:
            logger.warning("Min width > max width")
            return []
        if target_width < min_width or target_width > max_width:
            target_width = (min_width + max_width) / 2
            logger.info(f"Target width adjusted to {target_width}")
        
        model = cp_model.CpModel()
        
        # Estimate number of lots
        max_lots = int(total_length / min_width) + 1
        
        logger.debug(f"Solving subdivision: Length={total_length:.2f}, Min={min_width}, Max={max_width}, Target={target_width}")
        
        # Decision variables: lot widths (scaled to integers for CP)
        scale = 100  # 1cm precision
        lot_vars = [
            model.NewIntVar(
                0, 
                int(max_width * scale), 
                f'lot_{i}'
            )
            for i in range(max_lots)
        ]
        
        # Used lot indicators
        used = [model.NewBoolVar(f'used_{i}') for i in range(max_lots)]
        
        # Constraint: Sum of widths equals total length
        model.Add(
            sum(lot_vars[i] for i in range(max_lots)) == int(total_length * scale)
        )
        
        # Constraint: Lot ordering (if used[i], then used[i-1] must be true)
        for i in range(1, max_lots):
            model.Add(used[i] <= used[i-1])
        
        # Constraint: Connect lot values to usage
        for i in range(max_lots):
            model.Add(lot_vars[i] >= int(min_width * scale)).OnlyEnforceIf(used[i])
            model.Add(lot_vars[i] == 0).OnlyEnforceIf(used[i].Not())
        
        # Objective: Minimize deviation from target (weighted approach from Beauti_mode)
        # Deviation bound must accommodate unused lots (0 width -> deviation = target_width)
        dev_upper_bound = int(max(max_width, target_width) * 2 * scale)
        deviations = [
            model.NewIntVar(0, dev_upper_bound, f'dev_{i}')
            for i in range(max_lots)
        ]
        
        target_scaled = int(target_width * scale)
        for i in range(max_lots):
            model.AddAbsEquality(deviations[i], lot_vars[i] - target_scaled)
        
        # Enhanced objective: Maximize area while penalizing deviation (Beauti_mode Section 4)
        # Higher deviation_penalty_weight = more uniform lot sizes
        penalty_weight = int(deviation_penalty_weight)
        model.Maximize(sum(lot_vars) * 100 - sum(deviations) * penalty_weight)
        
        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit
        status = solver.Solve(model)
        
        # Extract solution
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            widths = []
            for i in range(max_lots):
                if solver.Value(used[i]):
                    widths.append(solver.Value(lot_vars[i]) / scale)
            logger.debug(f"Subdivision solved: {len(widths)} lots")
            return widths
        else:
            # Fallback: uniform division
            logger.warning(f"CP solver failed (Status: {solver.StatusName(status)}), using uniform fallback")
            num_lots = max(1, int(total_length / target_width))
            return [total_length / num_lots] * num_lots
    
    @staticmethod
    def subdivide_block(
        block_geom: Polygon, 
        spacing: float, 
        min_width: float, 
        max_width: float, 
        target_width: float, 
        time_limit: float = 5.0,
        setback_dist: float = 6.0
    ) -> Dict[str, Any]:
        """
        Subdivide a block into lots.
        
        Args:
            block_geom: Block geometry
            spacing: Grid spacing (for quality calculation)
            min_width: Minimum lot width
            max_width: Maximum lot width
            target_width: Target lot width
            time_limit: Solver time limit
            setback_dist: Building setback distance
            
        Returns:
            Dictionary with subdivision info:
            - geometry: Original block
            - type: 'residential' or 'park'
            - lots: List of lot info dicts
        """
        # Determine block quality
        original_area = spacing * spacing
        current_area = block_geom.area
        
        # Safety check for division
        if original_area <= 0:
            ratio = 0.0
        else:
            ratio = current_area / original_area
        
        result = {
            'geometry': block_geom,
            'type': 'unknown',
            'lots': []
        }
        
        # Fragmented blocks become parks
        if ratio < 0.6:
            result['type'] = 'park'
            return result
        
        # Good blocks become residential/commercial
        result['type'] = 'residential'
        
        # Use OBB length for subdivision (handles rotated blocks)
        # width is shorter dim, length is longer dim.
        # We assume we cut along the dominant edge (length).
        _, total_length, _ = get_obb_dimensions(block_geom)
        
        # Adaptive time limit based on block size
        adaptive_time = min(time_limit, max(0.5, total_length / 100))
        
        lot_widths = SubdivisionSolver.solve_subdivision(
            total_length, min_width, max_width, target_width, adaptive_time
        )
        
        # Use Orthogonal Slicer to generate lot geometries
        raw_lots = orthogonal_slice(block_geom, lot_widths)
        
        for lot_poly in raw_lots:
             # Calculate setback (buildable area)
             # simplify(0.1) handles minor artifacts from rotation/buffering
             buildable = lot_poly.buffer(-setback_dist).simplify(0.1)
             
             if buildable.is_empty or not buildable.is_valid:
                 buildable = None
                 
             result['lots'].append({
                 'geometry': lot_poly,
                 'width': lot_poly.area / total_length * len(lot_widths), # Approx width
                 'buildable': buildable
             })
        
        return result
