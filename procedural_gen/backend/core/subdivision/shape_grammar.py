"""Shape Grammar for rule-based lot generation.

Applies production rules to transform and refine lots,
similar to CityEngine's procedural grammar system.

Reference: docs/Procedural Generation.md - Section 2 (Shape Grammars)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional, Any
import logging
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union

from core.geometry import analyze_shape_quality, get_obb_dimensions

logger = logging.getLogger(__name__)


@dataclass
class GrammarRule:
    """A single production rule in the shape grammar."""
    
    name: str
    condition: Callable[[Polygon, Dict], bool]  # When to apply
    action: Callable[[Polygon, Dict], List[Polygon]]  # What to produce
    priority: int = 0  # Higher = apply first


@dataclass
class ShapeGrammarConfig:
    """Configuration for shape grammar system."""
    
    # Setbacks
    front_setback: float = 3.0  # meters
    side_setback: float = 2.0  # meters
    rear_setback: float = 3.0  # meters
    
    # Minimum dimensions
    min_lot_area: float = 1000.0  # m²
    min_lot_width: float = 20.0  # m
    
    # Access road
    access_road_width: float = 6.0  # m
    
    # Green space ratio
    green_space_ratio: float = 0.1  # 10% for green
    
    # Quality thresholds (relaxed for procedural generation)
    min_rectangularity: float = 0.60  # Lower to accept more shapes
    max_aspect_ratio: float = 6.0     # Higher to accept elongated lots


class ShapeGrammar:
    """CityEngine-style shape grammar for lot generation.
    
    Applies production rules to transform polygons according
    to configurable rules. Each rule has a condition and action.
    
    Built-in rules:
    - AddSetback: Add building setback
    - AddSidewalk: Add sidewalk along road
    - SplitToLots: Divide large block into lots
    - ConvertToGreen: Convert poor lots to green space
    
    Example:
        >>> grammar = ShapeGrammar(config)
        >>> grammar.add_rule(custom_rule)
        >>> result = grammar.apply(lots)
    """
    
    def __init__(self, config: Optional[ShapeGrammarConfig] = None):
        """Initialize shape grammar.
        
        Args:
            config: Grammar configuration
        """
        self.config = config or ShapeGrammarConfig()
        self.rules: List[GrammarRule] = []
        
        # Add default rules
        self._add_default_rules()
        
    def add_rule(self, rule: GrammarRule):
        """Add a production rule.
        
        Args:
            rule: Rule to add
        """
        self.rules.append(rule)
        # Sort by priority (descending)
        self.rules.sort(key=lambda r: -r.priority)
        
    def apply(
        self, 
        shapes: List[Polygon],
        context: Optional[Dict] = None
    ) -> Dict[str, List[Polygon]]:
        """Apply grammar rules to a list of shapes.
        
        Args:
            shapes: Input polygons
            context: Optional context data (e.g., road locations)
            
        Returns:
            Dictionary with categorized results:
            - 'lots': Valid building lots
            - 'setbacks': Setback areas
            - 'sidewalks': Sidewalk areas
            - 'green_spaces': Green areas
        """
        context = context or {}
        
        result = {
            'lots': [],
            'setbacks': [],
            'sidewalks': [],
            'green_spaces': [],
            'access_roads': []
        }
        
        # Process each shape
        for shape in shapes:
            if shape.is_empty:
                continue
                
            self._process_shape(shape, context, result)
            
        logger.info(
            f"Grammar applied: {len(result['lots'])} lots, "
            f"{len(result['green_spaces'])} green spaces"
        )
        
        return result
        
    def apply_to_lot(
        self, 
        lot: Polygon,
        context: Optional[Dict] = None
    ) -> Dict[str, Polygon]:
        """Apply grammar to create detailed lot with setbacks.
        
        Args:
            lot: Lot polygon
            context: Optional context data
            
        Returns:
            Dictionary with lot components:
            - 'buildable': Building footprint area
            - 'front_setback': Front setback area
            - 'side_setbacks': Side setback areas
            - 'rear_setback': Rear setback area
        """
        context = context or {}
        
        # Apply setbacks
        buildable = lot.buffer(-self.config.front_setback)
        
        if buildable.is_empty:
            return {'buildable': Polygon(), 'setbacks': lot}
            
        front_setback = lot.difference(buildable)
        
        return {
            'buildable': buildable,
            'front_setback': front_setback,
            'original': lot
        }
        
    def _add_default_rules(self):
        """Add built-in rules."""
        
        # Rule 1: Apply setbacks to valid lots
        def setback_condition(poly: Polygon, ctx: Dict) -> bool:
            _, is_valid = analyze_shape_quality(
                poly,
                min_rectangularity=self.config.min_rectangularity,
                max_aspect_ratio=self.config.max_aspect_ratio,
                min_area=self.config.min_lot_area
            )
            return is_valid
            
        def setback_action(poly: Polygon, ctx: Dict) -> List[Polygon]:
            # Create inner buildable area
            buildable = poly.buffer(-self.config.front_setback)
            if buildable.is_empty or not buildable.is_valid:
                return [poly]  # Keep original if setback fails
            return [buildable]
            
        self.rules.append(GrammarRule(
            name="apply_setback",
            condition=setback_condition,
            action=setback_action,
            priority=10
        ))
        
        # Rule 2: Convert invalid lots to green space
        def green_condition(poly: Polygon, ctx: Dict) -> bool:
            _, is_valid = analyze_shape_quality(
                poly,
                min_rectangularity=self.config.min_rectangularity,
                max_aspect_ratio=self.config.max_aspect_ratio,
                min_area=self.config.min_lot_area
            )
            return not is_valid and poly.area >= self.config.min_lot_area * 0.3
            
        def green_action(poly: Polygon, ctx: Dict) -> List[Polygon]:
            # Mark as green space (handled in categorization)
            ctx['_is_green'] = True
            return [poly]
            
        self.rules.append(GrammarRule(
            name="convert_to_green",
            condition=green_condition,
            action=green_action,
            priority=5
        ))
        
    def _process_shape(
        self, 
        shape: Polygon, 
        context: Dict,
        result: Dict[str, List[Polygon]]
    ):
        """Process a single shape through the grammar.
        
        Args:
            shape: Shape to process
            context: Context data
            result: Result dictionary to append to
        """
        local_ctx = dict(context)
        local_ctx['_is_green'] = False
        
        current_shapes = [shape]
        
        # Apply first matching rule
        for rule in self.rules:
            new_shapes = []
            
            for s in current_shapes:
                if rule.condition(s, local_ctx):
                    produced = rule.action(s, local_ctx)
                    new_shapes.extend(produced)
                else:
                    new_shapes.append(s)
                    
            current_shapes = new_shapes
            
        # Categorize results
        for s in current_shapes:
            if local_ctx.get('_is_green'):
                result['green_spaces'].append(s)
            else:
                # Check quality for final categorization
                _, is_valid = analyze_shape_quality(
                    s,
                    min_rectangularity=self.config.min_rectangularity,
                    max_aspect_ratio=self.config.max_aspect_ratio,
                    min_area=self.config.min_lot_area
                )
                
                if is_valid:
                    result['lots'].append(s)
                else:
                    result['green_spaces'].append(s)


def apply_shape_grammar(
    lots: List[Polygon],
    front_setback: float = 3.0,
    side_setback: float = 2.0,
    min_lot_area: float = 1000.0
) -> Dict[str, List[Polygon]]:
    """Convenience function to apply shape grammar.
    
    Args:
        lots: Input lot polygons
        front_setback: Front setback distance (m)
        side_setback: Side setback distance (m)
        min_lot_area: Minimum lot area (m²)
        
    Returns:
        Dictionary with categorized results
    """
    config = ShapeGrammarConfig(
        front_setback=front_setback,
        side_setback=side_setback,
        min_lot_area=min_lot_area
    )
    
    grammar = ShapeGrammar(config)
    return grammar.apply(lots)
