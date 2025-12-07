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

from core.config.settings import SubdivisionSettings, DEFAULT_SETTINGS

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
        time_limit: float = 5.0
    ) -> List[float]:
        """
        Solve optimal lot widths using constraint programming.
        
        Args:
            total_length: Total length to subdivide
            min_width: Minimum lot width
            max_width: Maximum lot width
            target_width: Target lot width
            time_limit: Solver time limit in seconds
            
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
        
        # Decision variables: lot widths (scaled to integers for CP)
        scale = 100  # 1cm precision
        lot_vars = [
            model.NewIntVar(
                int(min_width * scale), 
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
        
        # Objective: Minimize deviation from target
        deviations = [
            model.NewIntVar(0, int((max_width - min_width) * scale), f'dev_{i}')
            for i in range(max_lots)
        ]
        
        target_scaled = int(target_width * scale)
        for i in range(max_lots):
            model.AddAbsEquality(deviations[i], lot_vars[i] - target_scaled)
        
        model.Minimize(sum(deviations))
        
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
            logger.warning("CP solver failed, using uniform fallback")
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
        
        # Solve subdivision
        minx, miny, maxx, maxy = block_geom.bounds
        total_width = maxx - minx
        
        # Adaptive time limit based on block size
        adaptive_time = min(time_limit, max(0.5, total_width / 100))
        
        lot_widths = SubdivisionSolver.solve_subdivision(
            total_width, min_width, max_width, target_width, adaptive_time
        )
        
        # Create lot geometries
        current_x = minx
        
        for width in lot_widths:
            lot_poly = Polygon([
                (current_x, miny),
                (current_x + width, miny),
                (current_x + width, maxy),
                (current_x, maxy)
            ])
            
            # Clip to block boundary
            clipped = lot_poly.intersection(block_geom)
            if not clipped.is_empty and clipped.geom_type == 'Polygon':
                # Calculate setback (buildable area)
                buildable = clipped.buffer(-setback_dist)
                if buildable.is_empty or not buildable.is_valid:
                    buildable = None
                
                result['lots'].append({
                    'geometry': clipped,
                    'width': width,
                    'buildable': buildable
                })
            
            current_x += width
        
        return result
