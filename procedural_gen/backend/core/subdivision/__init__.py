"""Subdivision module for lot generation.

Contains algorithms for dividing blocks into lots:
- OBB Tree for hierarchical subdivision
- Shape Grammar for rule-based generation
- Constraint Refiner for OR-Tools integration
"""

from typing import List, Optional, Tuple
import logging
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union

from core.geometry import analyze_shape_quality

from .obb_tree import OBBTree, OBBTreeConfig, obb_tree_subdivide
from .shape_grammar import ShapeGrammar, ShapeGrammarConfig, apply_shape_grammar
from .constraint_refiner import ConstraintRefiner, refine_subdivision

logger = logging.getLogger(__name__)


def subdivide_site(
    site_boundary: Polygon,
    roads: Optional[List[LineString]] = None,
    min_lot_area: float = 1000.0,
    max_lot_area: float = 10000.0,
    target_lot_width: float = 40.0,
    use_shape_grammar: bool = True,
    **kwargs
) -> Tuple[List[Polygon], List[Polygon]]:
    """Subdivide site into lots using OBB Tree and Shape Grammar.
    
    Pipeline:
    1. Subtract roads from site to get buildable blocks
    2. Apply OBB Tree subdivision to each block
    3. Apply Shape Grammar rules for setbacks
    4. Optionally refine with constraint solver
    5. Filter by quality metrics
    
    Args:
        site_boundary: Site boundary polygon
        roads: Optional pre-computed road lines
        min_lot_area: Minimum lot area (m²)
        max_lot_area: Maximum lot area (m²)
        target_lot_width: Target lot width (m)
        use_shape_grammar: Apply shape grammar rules
        **kwargs: Additional options
        
    Returns:
        (lots, green_spaces) tuple
    """
    logger.info("Starting subdivision pipeline")
    
    lots = []
    green_spaces = []
    
    # Step 1: Subtract roads to get buildable blocks
    road_buffer_width = kwargs.get('road_buffer_width', 6.0)
    
    if roads:
        road_buffer = unary_union([r.buffer(road_buffer_width) for r in roads])
        buildable = site_boundary.difference(road_buffer)
    else:
        buildable = site_boundary
        
    # Handle MultiPolygon
    if buildable.geom_type == 'MultiPolygon':
        blocks = list(buildable.geoms)
    elif buildable.geom_type == 'Polygon':
        blocks = [buildable]
    else:
        blocks = []
        
    logger.info(f"Created {len(blocks)} buildable blocks")
    
    # Step 2: OBB Tree subdivision for each block
    obb_config = OBBTreeConfig(
        min_lot_area=min_lot_area,
        max_lot_area=max_lot_area,
        target_lot_width=target_lot_width,
        max_depth=kwargs.get('max_depth', 8)
    )
    
    raw_lots = []
    
    for block in blocks:
        if block.is_empty or block.area < min_lot_area * 0.5:
            # Too small - mark as green space
            if block.area > 50:  # Non-trivial area
                green_spaces.append(block)
            continue
            
        # Subdivide block
        tree = OBBTree(block, obb_config)
        block_lots = tree.subdivide()
        raw_lots.extend(block_lots)
        
    logger.info(f"OBB Tree created {len(raw_lots)} lots")
    
    # Step 3: Apply Shape Grammar (optional)
    if use_shape_grammar:
        grammar_config = ShapeGrammarConfig(
            front_setback=kwargs.get('front_setback', 3.0),
            side_setback=kwargs.get('side_setback', 2.0),
            min_lot_area=min_lot_area
        )
        
        grammar = ShapeGrammar(grammar_config)
        result = grammar.apply(raw_lots)
        
        lots = result['lots']
        green_spaces.extend(result['green_spaces'])
    else:
        # Just quality filter
        for lot in raw_lots:
            score, is_valid = analyze_shape_quality(
                lot,
                min_area=min_lot_area
            )
            
            if is_valid:
                lots.append(lot)
            else:
                green_spaces.append(lot)
                
    logger.info(f"Final: {len(lots)} lots, {len(green_spaces)} green spaces")
    
    return lots, green_spaces


def subdivide_block(
    block: Polygon,
    min_lot_area: float = 1000.0,
    max_lot_area: float = 10000.0,
    target_lot_width: float = 40.0
) -> List[Polygon]:
    """Subdivide a single block using OBB Tree.
    
    Args:
        block: Block polygon
        min_lot_area: Minimum lot area (m²)
        max_lot_area: Maximum lot area (m²)
        target_lot_width: Target width (m)
        
    Returns:
        List of lot polygons
    """
    return obb_tree_subdivide(
        block,
        min_lot_area=min_lot_area,
        max_lot_area=max_lot_area,
        target_lot_width=target_lot_width
    )


__all__ = [
    "subdivide_site",
    "subdivide_block",
    "OBBTree",
    "OBBTreeConfig",
    "obb_tree_subdivide",
    "ShapeGrammar",
    "ShapeGrammarConfig",
    "apply_shape_grammar",
    "ConstraintRefiner",
    "refine_subdivision"
]
