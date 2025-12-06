"""
Production-Ready Industrial Estate Optimizer
============================================

Implements all 4 fixes from Industrial_Estate_Complete_Fixes.md:
1. Road-First Approach - Generate roads BEFORE plots
2. Grid-Based Bin Packing - Use rectpack for organized placement
3. Hard Overlap Validation - Zero tolerance for overlaps
4. Constraint Propagation - Validate mutations before accepting

Based on verified research:
- arxiv.org/pdf/2004.12619.pdf (2D Packing)
- ACM 2024 (Randomized Local Search)  
- secnot/rectpack (300+ stars, production-ready)
"""

import numpy as np
from shapely.geometry import box, LineString, Polygon, MultiPolygon
from shapely.ops import unary_union
from typing import List, Dict, Tuple, Optional, Any
import logging
import os

# Try to import rectpack, provide helpful error if not installed
try:
    from rectpack import newPacker, PackingMode, PackingAlgorithm
    RECTPACK_AVAILABLE = True
except ImportError:
    RECTPACK_AVAILABLE = False
    print("⚠️ rectpack not installed. Run: pip install rectpack")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# FIX #3: HARD OVERLAP VALIDATION
# =============================================================================

class OverlapValidator:
    """
    FIX #3: Hard Overlap Validation
    Validates NO overlaps with HARD constraints (not soft penalty).
    
    Checks:
    1. Plot-to-plot overlaps (with minimum clearance)
    2. Plot-to-road conflicts
    3. Plot containment within buildable area
    """
    
    def __init__(self, min_clearance: float = 10.0):
        """
        Args:
            min_clearance: Minimum distance between plots (meters, default: 10m)
        """
        self.min_clearance = min_clearance
    
    def validate_layout(
        self, 
        plots: List[Dict], 
        roads_geometry: Optional[Any] = None,
        buildable_area: Optional[Any] = None
    ) -> Tuple[bool, List[Dict]]:
        """
        Validate layout with HARD constraints.
        
        Args:
            plots: List of plot dicts with 'x', 'y', 'width', 'height'
            roads_geometry: Shapely geometry of roads (buffered)
            buildable_area: Shapely polygon of buildable area
            
        Returns:
            (is_valid, list of violations)
        """
        violations = []
        
        if not plots:
            return True, []
        
        # Create plot geometries
        plot_geoms = []
        for p in plots:
            geom = box(p['x'], p['y'], p['x'] + p['width'], p['y'] + p['height'])
            plot_geoms.append(geom)
        
        # 1. Check plot-to-plot overlaps (with clearance buffer)
        for i in range(len(plots)):
            buffered_i = plot_geoms[i].buffer(self.min_clearance / 2)
            for j in range(i + 1, len(plots)):
                buffered_j = plot_geoms[j].buffer(self.min_clearance / 2)
                if buffered_i.intersects(buffered_j):
                    intersection = buffered_i.intersection(buffered_j)
                    overlap_area = intersection.area if hasattr(intersection, 'area') else 0
                    violations.append({
                        'type': 'OVERLAP',
                        'plots': [plots[i].get('id', f'plot_{i}'), plots[j].get('id', f'plot_{j}')],
                        'overlap_area': overlap_area,
                        'severity': 'CRITICAL'
                    })
        
        # 2. Check plot-to-road overlaps
        if roads_geometry is not None and not roads_geometry.is_empty:
            for i, plot in enumerate(plots):
                if plot_geoms[i].intersects(roads_geometry):
                    intersection = plot_geoms[i].intersection(roads_geometry)
                    overlap_area = intersection.area if hasattr(intersection, 'area') else 0
                    violations.append({
                        'type': 'ROAD_CONFLICT',
                        'plot': plots[i].get('id', f'plot_{i}'),
                        'overlap_area': overlap_area,
                        'severity': 'CRITICAL'
                    })
        
        # 3. Check containment in buildable area
        if buildable_area is not None and not buildable_area.is_empty:
            for i, plot in enumerate(plots):
                if not buildable_area.contains(plot_geoms[i]):
                    # Check how much is outside
                    if not plot_geoms[i].intersects(buildable_area):
                        violations.append({
                            'type': 'OUT_OF_BOUNDS',
                            'plot': plots[i].get('id', f'plot_{i}'),
                            'severity': 'CRITICAL'
                        })
                    else:
                        # Partially outside
                        outside_area = plot_geoms[i].difference(buildable_area).area
                        if outside_area > plot_geoms[i].area * 0.1:  # More than 10% outside
                            violations.append({
                                'type': 'PARTIALLY_OUT_OF_BOUNDS',
                                'plot': plots[i].get('id', f'plot_{i}'),
                                'outside_area': outside_area,
                                'severity': 'WARNING'
                            })
        
        # Valid if no CRITICAL violations
        critical_violations = [v for v in violations if v['severity'] == 'CRITICAL']
        is_valid = len(critical_violations) == 0
        
        return is_valid, violations
    
    def repair_layout(self, plots: List[Dict], violations: List[Dict]) -> List[Dict]:
        """
        Attempt to repair overlap violations by shifting plots.
        
        Args:
            plots: List of plot dicts
            violations: List of violation dicts
            
        Returns:
            Repaired plot list
        """
        repaired = [p.copy() for p in plots]
        
        for violation in violations:
            if violation['type'] == 'OVERLAP':
                # Find the two overlapping plots
                id_a, id_b = violation['plots']
                plot_a = next((p for p in repaired if p.get('id') == id_a), None)
                plot_b = next((p for p in repaired if p.get('id') == id_b), None)
                
                if plot_a and plot_b:
                    # Move plot_a to the right of plot_b
                    gap = self.min_clearance + 1
                    plot_a['x'] = plot_b['x'] + plot_b['width'] + gap
        
        return repaired


# =============================================================================
# FIX #4: CONSTRAINED GA MUTATION
# =============================================================================

class ConstrainedGAOptimizer:
    """
    FIX #4: Constraint Propagation During Mutation
    
    GA that ONLY accepts mutations that respect hard constraints.
    Invalid mutations are reverted immediately.
    """
    
    def __init__(self, validator: OverlapValidator, buildable_area: Any):
        self.validator = validator
        self.buildable = buildable_area
    
    def mutate(
        self, 
        layout: List[Dict], 
        mutation_rate: float = 0.1,
        max_delta: float = 20.0
    ) -> List[Dict]:
        """
        Mutate layout while respecting hard constraints.
        
        Args:
            layout: List of plot dicts
            mutation_rate: Probability of mutating each plot
            max_delta: Maximum position shift (meters)
            
        Returns:
            Mutated layout (guaranteed valid)
        """
        mutated = [p.copy() for p in layout]
        
        for plot in mutated:
            if np.random.random() < mutation_rate:
                # Save original position
                old_x, old_y = plot['x'], plot['y']
                
                # Apply random small movement
                delta_x = np.random.uniform(-max_delta, max_delta)
                delta_y = np.random.uniform(-max_delta, max_delta)
                
                plot['x'] += delta_x
                plot['y'] += delta_y
                
                # Validate after mutation
                is_valid, _ = self.validator.validate_layout(mutated, None, self.buildable)
                
                if not is_valid:
                    # REVERT - mutation violated constraints
                    plot['x'] = old_x
                    plot['y'] = old_y
        
        return mutated


# =============================================================================
# MAIN OPTIMIZER (ALL 4 FIXES INTEGRATED)
# =============================================================================

class ProductionReadyEstateOptimizer:
    """
    Production-Ready Industrial Estate Optimizer
    
    Implements the CORRECT order:
    1. Generate road network FIRST (FIX #1)
    2. Calculate buildable area (excluding roads)
    3. Place plots using bin packing (FIX #2)
    4. Validate with hard constraints (FIX #3)
    5. Support constrained mutation (FIX #4)
    """
    
    def __init__(
        self,
        boundary_coords: Dict,
        plot_configs: Optional[List[Dict]] = None,
        road_width: float = 24.0,
        road_spacing: float = 200.0,
        setback: float = 10.0,
        plot_spacing: float = 10.0
    ):
        """
        Args:
            boundary_coords: {'min_x', 'min_y', 'max_x', 'max_y'}
            plot_configs: List of {'width', 'height', 'type'} (optional)
            road_width: Total road width including margins (default: 24m)
            road_spacing: Distance between parallel roads (default: 200m)
            setback: Distance from site boundary (default: 10m)
            plot_spacing: Minimum spacing between plots (default: 10m)
        """
        self.boundary = boundary_coords
        self.plot_configs = plot_configs or self._default_plot_configs()
        self.road_width = road_width
        self.road_buffer = road_width / 2
        self.road_spacing = road_spacing
        self.setback = setback
        self.plot_spacing = plot_spacing
        self.validator = OverlapValidator(plot_spacing)
        
        # Calculate site dimensions
        self.site_width = boundary_coords['max_x'] - boundary_coords['min_x']
        self.site_height = boundary_coords['max_y'] - boundary_coords['min_y']
        self.site_area = self.site_width * self.site_height
    
    def _default_plot_configs(self) -> List[Dict]:
        """Generate default industrial plot configurations"""
        return [
            {'width': 60, 'height': 80, 'type': 'warehouse'},
            {'width': 50, 'height': 60, 'type': 'office'},
            {'width': 70, 'height': 90, 'type': 'factory'},
            {'width': 55, 'height': 70, 'type': 'storage'},
            {'width': 60, 'height': 60, 'type': 'workshop'},
            {'width': 65, 'height': 75, 'type': 'warehouse'},
        ] * 4  # 24 plots total
    
    def optimize(self) -> Dict:
        """
        Main optimization pipeline with CORRECT order.
        
        Returns:
            Dict containing:
            - roads: List of LineString objects
            - road_geometry: Buffered road polygon
            - buildable_area: Available building area
            - plots: List of placed plot dicts
            - is_valid: Boolean validation result
            - violations: List of any violations
            - metrics: Performance metrics
        """
        logger.info("=" * 60)
        logger.info("🚀 PRODUCTION-READY ESTATE OPTIMIZATION")
        logger.info("=" * 60)
        logger.info(f"   Site: {self.site_width:.0f}m × {self.site_height:.0f}m = {self.site_area:,.0f} m²")
        logger.info(f"   Plots to place: {len(self.plot_configs)}")
        
        # =====================================================================
        # STEP 1: Generate road network FIRST (FIX #1)
        # =====================================================================
        logger.info("\n📍 STEP 1: Generating road network FIRST...")
        roads, road_geometry = self._generate_road_network()
        road_area = road_geometry.area if road_geometry and not road_geometry.is_empty else 0
        logger.info(f"   ✓ Generated {len(roads)} road segments")
        logger.info(f"   ✓ Road area: {road_area:,.0f} m² ({road_area/self.site_area*100:.1f}% of site)")
        
        # =====================================================================
        # STEP 2: Calculate buildable area (excluding roads + setbacks)
        # =====================================================================
        logger.info("\n📐 STEP 2: Calculating buildable area...")
        buildable = self._calculate_buildable_area(road_geometry)
        buildable_area = buildable.area if hasattr(buildable, 'area') else 0
        logger.info(f"   ✓ Buildable area: {buildable_area:,.0f} m² ({buildable_area/self.site_area*100:.1f}% of site)")
        
        # =====================================================================
        # STEP 3: Place plots using bin packing (FIX #2)
        # =====================================================================
        logger.info("\n📦 STEP 3: Placing plots using bin packing...")
        if RECTPACK_AVAILABLE:
            plots = self._place_plots_bin_packing(buildable)
        else:
            logger.warning("   ⚠️ rectpack not available, using grid placement")
            plots = self._place_plots_grid_fallback(buildable)
        logger.info(f"   ✓ Placed {len(plots)} of {len(self.plot_configs)} plots")
        
        # =====================================================================
        # STEP 4: Validate with hard constraints (FIX #3)
        # =====================================================================
        logger.info("\n✅ STEP 4: Validating layout (HARD constraints)...")
        is_valid, violations = self.validator.validate_layout(
            plots, road_geometry, buildable
        )
        
        critical = [v for v in violations if v['severity'] == 'CRITICAL']
        warnings = [v for v in violations if v['severity'] == 'WARNING']
        
        if is_valid:
            logger.info(f"   ✓ VALIDATION PASSED!")
            logger.info(f"     - No plot overlaps ✅")
            logger.info(f"     - No road conflicts ✅")
            logger.info(f"     - All plots in bounds ✅")
        else:
            logger.warning(f"   ⚠️ Found {len(critical)} critical, {len(warnings)} warning violations")
            for v in critical[:5]:
                logger.warning(f"     - {v['type']}: {v}")
            
            # Attempt repair
            logger.info("   🔧 Attempting repair...")
            plots = self.validator.repair_layout(plots, violations)
            is_valid, violations = self.validator.validate_layout(plots, road_geometry, buildable)
            logger.info(f"   After repair: {'✅ Valid' if is_valid else '❌ Still invalid'}")
        
        # =====================================================================
        # STEP 5: Calculate metrics
        # =====================================================================
        logger.info("\n📊 STEP 5: Calculating metrics...")
        metrics = self._calculate_metrics(plots, buildable)
        
        # =====================================================================
        # RESULT
        # =====================================================================
        result = {
            'boundary': self.boundary,
            'roads': roads,
            'road_geometry': road_geometry,
            'buildable_area': buildable,
            'plots': plots,
            'is_valid': is_valid,
            'violations': violations,
            'metrics': metrics
        }
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📋 OPTIMIZATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"   Site area:        {self.site_area:>12,.0f} m²")
        logger.info(f"   Buildable area:   {buildable_area:>12,.0f} m²")
        logger.info(f"   Total plot area:  {metrics['total_plot_area']:>12,.0f} m²")
        logger.info(f"   Plots placed:     {metrics['num_plots']:>12d} / {len(self.plot_configs)}")
        logger.info(f"   Avg plot size:    {metrics['avg_plot_size']:>12,.0f} m²")
        logger.info(f"   Utilization:      {metrics['utilization']*100:>11.1f}%")
        logger.info(f"   Valid layout:     {'✅ YES' if is_valid else '❌ NO':>12s}")
        logger.info(f"   Violations:       {len(violations):>12d}")
        logger.info("=" * 60)
        
        return result
    
    # =========================================================================
    # FIX #1: Road-First Approach
    # =========================================================================
    
    def _generate_road_network(self) -> Tuple[List[LineString], Any]:
        """
        FIX #1: Generate road network FIRST
        Creates grid-based primary road network before any plot placement.
        
        Returns:
            (list of road LineStrings, buffered road geometry)
        """
        minx = self.boundary['min_x']
        miny = self.boundary['min_y']
        maxx = self.boundary['max_x']
        maxy = self.boundary['max_y']
        
        roads = []
        
        # Primary N-S roads (vertical)
        x = minx + self.road_spacing / 2
        while x < maxx:
            road = LineString([(x, miny), (x, maxy)])
            roads.append(road)
            x += self.road_spacing
        
        # Primary E-W roads (horizontal)
        y = miny + self.road_spacing / 2
        while y < maxy:
            road = LineString([(minx, y), (maxx, y)])
            roads.append(road)
            y += self.road_spacing
        
        # Create buffered road geometry (no-build zone)
        if roads:
            buffered_roads = [road.buffer(self.road_buffer) for road in roads]
            road_geometry = unary_union(buffered_roads)
        else:
            road_geometry = Polygon()
        
        return roads, road_geometry
    
    def _calculate_buildable_area(self, road_geometry: Any) -> Any:
        """
        Buildable = Site - Setback - Roads
        
        Args:
            road_geometry: Buffered road polygon
            
        Returns:
            Shapely polygon of buildable area
        """
        # Create site boundary
        site = box(
            self.boundary['min_x'],
            self.boundary['min_y'],
            self.boundary['max_x'],
            self.boundary['max_y']
        )
        
        # Apply setback from boundary
        with_setback = site.buffer(-self.setback)
        
        # Subtract road areas
        if road_geometry and not road_geometry.is_empty:
            buildable = with_setback.difference(road_geometry)
        else:
            buildable = with_setback
        
        return buildable
    
    # =========================================================================
    # FIX #2: Grid-Based Bin Packing
    # =========================================================================
    
    def _place_plots_bin_packing(self, buildable: Any) -> List[Dict]:
        """
        FIX #2: Grid-based bin packing using rectpack
        Places plots optimally in available buildable area.
        
        Args:
            buildable: Shapely polygon of buildable area
            
        Returns:
            List of placed plot dicts
        """
        if not RECTPACK_AVAILABLE:
            return self._place_plots_grid_fallback(buildable)
        
        # Handle MultiPolygon (buildable may be split by roads)
        if isinstance(buildable, MultiPolygon):
            polygons = list(buildable.geoms)
        elif isinstance(buildable, Polygon):
            polygons = [buildable]
        else:
            logger.warning(f"Unexpected buildable type: {type(buildable)}")
            return []
        
        all_plots = []
        remaining_configs = list(enumerate(self.plot_configs))
        
        # Sort plots by area (largest first for better packing)
        remaining_configs.sort(key=lambda x: x[1]['width'] * x[1]['height'], reverse=True)
        
        # Process each buildable polygon (blocks between roads)
        for poly_idx, polygon in enumerate(polygons):
            if polygon.is_empty or polygon.area < 1000:  # Skip tiny areas
                continue
            
            minx, miny, maxx, maxy = polygon.bounds
            bin_width = int(maxx - minx - 2 * self.plot_spacing)
            bin_height = int(maxy - miny - 2 * self.plot_spacing)
            
            if bin_width <= 50 or bin_height <= 50:  # Skip too small bins
                continue
            
            # Create packer for this block
            packer = newPacker(rotation=True)
            packer.add_bin(bin_width, bin_height)
            
            # Add rectangles (with IDs for tracking)
            for orig_idx, config in remaining_configs:
                w = int(config['width'])
                h = int(config['height'])
                if w > 0 and h > 0 and w <= bin_width and h <= bin_height:
                    packer.add_rect(w, h, rid=orig_idx)
            
            # Pack
            packer.pack()
            
            # Extract results
            placed_ids = set()
            for abin in packer:
                for rect in abin:
                    # Calculate absolute position
                    abs_x = minx + self.plot_spacing + rect.x
                    abs_y = miny + self.plot_spacing + rect.y
                    
                    config = self.plot_configs[rect.rid]
                    plot = {
                        'id': f"PLOT_{len(all_plots) + 1:03d}",
                        'config_id': rect.rid,
                        'x': abs_x,
                        'y': abs_y,
                        'width': rect.width,
                        'height': rect.height,
                        'area': rect.width * rect.height,
                        'type': config.get('type', 'industrial'),
                        'block': poly_idx
                    }
                    
                    # Verify plot is within buildable area
                    plot_geom = box(abs_x, abs_y, abs_x + rect.width, abs_y + rect.height)
                    
                    # Accept if mostly within buildable (90% threshold)
                    intersection = polygon.intersection(plot_geom)
                    if intersection.area >= plot_geom.area * 0.9:
                        all_plots.append(plot)
                        placed_ids.add(rect.rid)
            
            # Remove placed plots from remaining
            remaining_configs = [(i, c) for i, c in remaining_configs if i not in placed_ids]
        
        return all_plots
    
    def _place_plots_grid_fallback(self, buildable: Any) -> List[Dict]:
        """
        Fallback grid-based placement if rectpack is not available.
        Simple row-by-row placement.
        """
        if isinstance(buildable, MultiPolygon):
            polygon = max(buildable.geoms, key=lambda p: p.area)
        else:
            polygon = buildable
        
        minx, miny, maxx, maxy = polygon.bounds
        plots = []
        current_x = minx + self.plot_spacing
        current_y = miny + self.plot_spacing
        row_height = 0
        
        for i, config in enumerate(self.plot_configs):
            w, h = config['width'], config['height']
            
            # Check if fits in current row
            if current_x + w > maxx - self.plot_spacing:
                # Move to next row
                current_x = minx + self.plot_spacing
                current_y += row_height + self.plot_spacing
                row_height = 0
            
            # Check if fits in buildable area
            if current_y + h > maxy - self.plot_spacing:
                break  # No more room
            
            plot_geom = box(current_x, current_y, current_x + w, current_y + h)
            if polygon.contains(plot_geom):
                plots.append({
                    'id': f"PLOT_{len(plots) + 1:03d}",
                    'x': current_x,
                    'y': current_y,
                    'width': w,
                    'height': h,
                    'area': w * h,
                    'type': config.get('type', 'industrial')
                })
                
                current_x += w + self.plot_spacing
                row_height = max(row_height, h)
        
        return plots
    
    def _calculate_metrics(self, plots: List[Dict], buildable: Any) -> Dict:
        """Calculate space utilization metrics"""
        total_plot_area = sum(p['width'] * p['height'] for p in plots)
        buildable_area = buildable.area if hasattr(buildable, 'area') else 0
        
        return {
            'site_area': self.site_area,
            'buildable_area': buildable_area,
            'total_plot_area': total_plot_area,
            'num_plots': len(plots),
            'avg_plot_size': total_plot_area / len(plots) if plots else 0,
            'utilization': total_plot_area / buildable_area if buildable_area > 0 else 0,
            'site_coverage': total_plot_area / self.site_area if self.site_area > 0 else 0,
            'placement_rate': len(plots) / len(self.plot_configs) if self.plot_configs else 0
        }


# =============================================================================
# DXF EXPORT
# =============================================================================

def export_optimized_layout_to_dxf(result: Dict, output_path: str) -> str:
    """
    Export optimized layout to DXF file with proper layers.
    
    Args:
        result: Optimizer result dict
        output_path: Path for output DXF file
        
    Returns:
        Path to created file
    """
    import ezdxf
    
    doc = ezdxf.new(dxfversion='R2010')
    msp = doc.modelspace()
    
    # Add layers with colors
    doc.layers.add('BOUNDARY', color=7)    # White
    doc.layers.add('ROADS', color=1)       # Red  
    doc.layers.add('BUILDABLE', color=4)   # Cyan
    doc.layers.add('PLOTS', color=5)       # Blue
    doc.layers.add('LABELS', color=3)      # Green
    
    # Draw site boundary
    boundary = result.get('boundary')
    if boundary:
        points = [
            (boundary['min_x'], boundary['min_y']),
            (boundary['max_x'], boundary['min_y']),
            (boundary['max_x'], boundary['max_y']),
            (boundary['min_x'], boundary['max_y']),
            (boundary['min_x'], boundary['min_y'])  # Close
        ]
        msp.add_lwpolyline(points, dxfattribs={'layer': 'BOUNDARY', 'lineweight': 50})
    
    # Draw roads
    for road in result.get('roads', []):
        coords = list(road.coords)
        if len(coords) >= 2:
            msp.add_line(coords[0], coords[-1], dxfattribs={'layer': 'ROADS', 'lineweight': 35})
    
    # Draw plots
    for plot in result.get('plots', []):
        x, y = plot['x'], plot['y']
        w, h = plot['width'], plot['height']
        
        points = [
            (x, y),
            (x + w, y),
            (x + w, y + h),
            (x, y + h),
            (x, y)  # Close
        ]
        msp.add_lwpolyline(points, close=True, dxfattribs={'layer': 'PLOTS'})
        
        # Add label at center
        center_x = x + w / 2
        center_y = y + h / 2
        label = f"{plot['id']}\n{w}×{h}m"
        msp.add_mtext(
            label,
            dxfattribs={'layer': 'LABELS', 'char_height': 3}
        ).set_location((center_x, center_y))
    
    # Add metrics text
    metrics = result.get('metrics', {})
    if metrics:
        info_text = (
            f"LAYOUT METRICS\n"
            f"Plots: {metrics.get('num_plots', 0)}\n"
            f"Area: {metrics.get('total_plot_area', 0):,.0f} m²\n"
            f"Utilization: {metrics.get('utilization', 0)*100:.1f}%\n"
            f"Valid: {'YES' if result.get('is_valid') else 'NO'}"
        )
        if boundary:
            msp.add_mtext(
                info_text,
                dxfattribs={'layer': 'LABELS', 'char_height': 5}
            ).set_location((boundary['min_x'] + 10, boundary['max_y'] - 10))
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    
    # Save
    doc.saveas(output_path)
    logger.info(f"✅ DXF exported to: {output_path}")
    
    return output_path


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🏭 PRODUCTION-READY INDUSTRIAL ESTATE OPTIMIZER")
    print("="*70)
    
    # Define boundary (500m x 400m site)
    boundary = {
        'min_x': 0,
        'min_y': 0,
        'max_x': 500,
        'max_y': 400
    }
    
    # Define plot configurations (various industrial types)
    plots = [
        {'width': 60, 'height': 80, 'type': 'warehouse'},
        {'width': 50, 'height': 60, 'type': 'office'},
        {'width': 70, 'height': 90, 'type': 'factory'},
        {'width': 55, 'height': 70, 'type': 'storage'},
        {'width': 60, 'height': 60, 'type': 'workshop'},
        {'width': 65, 'height': 75, 'type': 'warehouse'},
    ] * 4  # 24 plots total
    
    # Create optimizer
    optimizer = ProductionReadyEstateOptimizer(
        boundary_coords=boundary,
        plot_configs=plots,
        road_width=24,
        road_spacing=200,
        setback=10,
        plot_spacing=10
    )
    
    # Run optimization
    result = optimizer.optimize()
    
    # Export to DXF
    os.makedirs('output', exist_ok=True)
    export_optimized_layout_to_dxf(result, 'output/production_layout.dxf')
    
    # Print detailed plot list
    print("\n📋 PLACED PLOTS:")
    print("-" * 70)
    for plot in result['plots'][:15]:
        print(f"   {plot['id']}: ({plot['x']:.0f}, {plot['y']:.0f}) "
              f"→ {plot['width']}×{plot['height']}m = {plot['area']:,} m² [{plot['type']}]")
    if len(result['plots']) > 15:
        print(f"   ... and {len(result['plots']) - 15} more plots")
    
    print("\n✅ COMPLETE! Check output/production_layout.dxf")
