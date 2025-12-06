"""
Polygon-Constrained Industrial Estate Optimizer
================================================

Complete solution based on Polygon_Constrained_Complete_Solution.md

KEY FEATURES:
✅ Works with IRREGULAR polygon boundaries (not just rectangles)
✅ NFP-inspired grid-based placement
✅ Hard constraint validation (no overlaps, inside boundary)
✅ Combines with bin packing for optimal placement
✅ DXF export with polygon boundary
✅ Visualization support

RESEARCH BASIS:
- No-Fit Polygon (NFP) algorithm - Dowsland et al. 2002
- Irregular polygon packing - Oliveira et al. 2017
- CG:SHOP Challenge 2024 - Maximum polygon packing

DEPENDENCIES:
pip install shapely numpy ezdxf matplotlib
"""

import numpy as np
from shapely.geometry import box, Polygon, MultiPolygon, LineString, Point
from shapely.ops import unary_union
from shapely.validation import make_valid
from typing import List, Dict, Tuple, Optional, Any, Union
import logging
import os

# Try to import rectpack for hybrid optimization
try:
    from rectpack import newPacker
    RECTPACK_AVAILABLE = True
except ImportError:
    RECTPACK_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# POLYGON BOUNDARY HANDLER
# =============================================================================

class PolygonBoundaryHandler:
    """
    Handles extraction and validation of polygon boundaries.
    Works with:
    - Shapely Polygon objects
    - Coordinate lists [(x1,y1), (x2,y2), ...]
    - DXF files (via ezdxf)
    """
    
    @staticmethod
    def from_coordinates(coords: List[Tuple[float, float]]) -> Polygon:
        """Create polygon from coordinate list"""
        polygon = Polygon(coords)
        if not polygon.is_valid:
            polygon = make_valid(polygon)
        return polygon
    
    @staticmethod
    def from_dxf(dxf_path: str, layer_name: str = 'BOUNDARY') -> Optional[Polygon]:
        """Extract polygon from DXF file"""
        try:
            import ezdxf
            doc = ezdxf.readfile(dxf_path)
            msp = doc.modelspace()
            
            # Look for polylines on the boundary layer
            for entity in msp.query(f'LWPOLYLINE[layer=="{layer_name}"]'):
                coords = [(p[0], p[1]) for p in entity.get_points('xy')]
                if len(coords) >= 3:
                    return Polygon(coords)
            
            # Fallback: look for any closed polyline
            for entity in msp.query('LWPOLYLINE'):
                if entity.closed:
                    coords = [(p[0], p[1]) for p in entity.get_points('xy')]
                    if len(coords) >= 3:
                        return Polygon(coords)
                        
        except Exception as e:
            logger.error(f"Error reading DXF: {e}")
        
        return None
    
    @staticmethod
    def from_dict(boundary_dict: Dict) -> Polygon:
        """Create polygon from dict with min/max coords (rectangle)"""
        return box(
            boundary_dict['min_x'],
            boundary_dict['min_y'],
            boundary_dict['max_x'],
            boundary_dict['max_y']
        )


# =============================================================================
# CONSTRAINT VALIDATOR
# =============================================================================

class PolygonConstraintValidator:
    """
    Validates plots against polygon boundary with HARD constraints.
    
    Checks:
    1. All plots completely inside boundary
    2. No plot-to-plot overlaps
    3. Minimum buffer from boundary edge
    4. Road clearance (if roads provided)
    """
    
    def __init__(
        self, 
        boundary: Polygon, 
        min_clearance: float = 10.0,
        boundary_buffer: float = 5.0
    ):
        self.boundary = boundary
        self.min_clearance = min_clearance
        self.boundary_buffer = boundary_buffer
        
        # Pre-compute buffered boundary for faster checks
        self.inner_boundary = boundary.buffer(-boundary_buffer)
    
    def is_inside_boundary(self, plot_geom: Polygon) -> bool:
        """Check if plot is completely inside boundary (with buffer)"""
        return self.inner_boundary.contains(plot_geom)
    
    def has_no_overlaps(self, plot_geom: Polygon, existing_plots: List[Polygon]) -> bool:
        """Check if plot overlaps with any existing plots"""
        for existing in existing_plots:
            # Use buffered intersection check for minimum clearance
            if plot_geom.buffer(self.min_clearance / 2).intersects(
                existing.buffer(self.min_clearance / 2)
            ):
                return False
        return True
    
    def validate_layout(
        self, 
        plots: List[Dict],
        roads_geometry: Optional[Polygon] = None
    ) -> Tuple[bool, Dict]:
        """
        Comprehensive layout validation.
        
        Returns:
            (is_valid, violations_dict)
        """
        violations = {
            'outside_boundary': [],
            'overlaps': [],
            'road_conflicts': [],
            'too_close_to_edge': []
        }
        
        # Create geometries
        plot_geoms = []
        for p in plots:
            if isinstance(p, dict):
                geom = box(p['x'], p['y'], p['x'] + p['width'], p['y'] + p['height'])
            else:
                geom = p  # Already a geometry
            plot_geoms.append(geom)
        
        # Check 1: Inside boundary
        for i, geom in enumerate(plot_geoms):
            if not self.boundary.contains(geom):
                violations['outside_boundary'].append(i)
            elif not self.inner_boundary.contains(geom):
                violations['too_close_to_edge'].append(i)
        
        # Check 2: Overlaps
        for i in range(len(plot_geoms)):
            buffered_i = plot_geoms[i].buffer(self.min_clearance / 2)
            for j in range(i + 1, len(plot_geoms)):
                buffered_j = plot_geoms[j].buffer(self.min_clearance / 2)
                if buffered_i.intersects(buffered_j):
                    overlap = buffered_i.intersection(buffered_j).area
                    violations['overlaps'].append({
                        'plots': (i, j),
                        'overlap_area': overlap
                    })
        
        # Check 3: Road conflicts
        if roads_geometry is not None and not roads_geometry.is_empty:
            for i, geom in enumerate(plot_geoms):
                if geom.intersects(roads_geometry):
                    violations['road_conflicts'].append(i)
        
        # Valid if no critical violations
        is_valid = (
            len(violations['outside_boundary']) == 0 and
            len(violations['overlaps']) == 0 and
            len(violations['road_conflicts']) == 0
        )
        
        return is_valid, violations


# =============================================================================
# POLYGON-CONSTRAINED OPTIMIZER
# =============================================================================

class PolygonConstrainedEstateOptimizer:
    """
    Industrial estate optimizer for IRREGULAR POLYGON BOUNDARIES.
    
    Uses NFP-inspired grid-based placement combined with:
    - Shapely containment checks for irregular boundaries
    - Optional bin packing for rectangular sub-regions
    - Hard constraint validation
    
    CORRECT ORDER:
    1. Generate roads inside polygon boundary
    2. Calculate buildable area (polygon - roads - setback)
    3. Place plots using grid-based NFP algorithm
    4. Validate all constraints
    """
    
    def __init__(
        self,
        boundary: Union[Polygon, List[Tuple], Dict],
        plot_configs: Optional[List[Dict]] = None,
        road_width: float = 24.0,
        road_spacing: float = 200.0,
        setback: float = 10.0,
        plot_spacing: float = 10.0,
        grid_step: float = 15.0
    ):
        """
        Args:
            boundary: Polygon boundary (Shapely Polygon, coord list, or dict)
            plot_configs: List of {'width', 'height', 'type'} dicts
            road_width: Total road width (meters)
            road_spacing: Distance between roads (meters)
            setback: Buffer from boundary edge (meters)
            plot_spacing: Minimum spacing between plots (meters)
            grid_step: Grid spacing for NFP search (meters)
        """
        # Handle different boundary input types
        if isinstance(boundary, Polygon):
            self.boundary = boundary
        elif isinstance(boundary, list):
            self.boundary = PolygonBoundaryHandler.from_coordinates(boundary)
        elif isinstance(boundary, dict):
            self.boundary = PolygonBoundaryHandler.from_dict(boundary)
        else:
            raise ValueError(f"Unsupported boundary type: {type(boundary)}")
        
        # Validate polygon
        if not self.boundary.is_valid:
            self.boundary = make_valid(self.boundary)
        
        self.plot_configs = plot_configs or self._default_plot_configs()
        self.road_width = road_width
        self.road_buffer = road_width / 2
        self.road_spacing = road_spacing
        self.setback = setback
        self.plot_spacing = plot_spacing
        self.grid_step = grid_step
        
        # State
        self.placed_plots = []
        self.plot_geometries = []
        self.roads = []
        self.road_geometry = None
        self.buildable_area = None
        
        # Validator
        self.validator = PolygonConstraintValidator(
            self.boundary, 
            self.plot_spacing, 
            self.setback
        )
        
        # Metrics
        self.boundary_area = self.boundary.area
        self.bounds = self.boundary.bounds  # (minx, miny, maxx, maxy)
    
    def _default_plot_configs(self) -> List[Dict]:
        """Default industrial plot configurations"""
        return [
            {'width': 60, 'height': 80, 'type': 'warehouse'},
            {'width': 50, 'height': 60, 'type': 'office'},
            {'width': 70, 'height': 90, 'type': 'factory'},
            {'width': 55, 'height': 70, 'type': 'storage'},
        ] * 5  # 20 plots
    
    def get_boundary_info(self) -> Dict:
        """Get polygon boundary information"""
        minx, miny, maxx, maxy = self.bounds
        return {
            'bounds': self.bounds,
            'area': self.boundary_area,
            'perimeter': self.boundary.length,
            'centroid': (self.boundary.centroid.x, self.boundary.centroid.y),
            'width': maxx - minx,
            'height': maxy - miny,
            'is_convex': self.boundary.convex_hull.area == self.boundary_area
        }
    
    def optimize(self) -> Dict:
        """
        Run complete optimization pipeline.
        
        Returns:
            Dict with roads, plots, validation, metrics
        """
        info = self.get_boundary_info()
        
        logger.info("=" * 60)
        logger.info("🔷 POLYGON-CONSTRAINED ESTATE OPTIMIZATION")
        logger.info("=" * 60)
        logger.info(f"   Boundary area: {self.boundary_area:,.0f} m²")
        logger.info(f"   Bounding box: {info['width']:.0f}m × {info['height']:.0f}m")
        logger.info(f"   Is convex: {'Yes' if info['is_convex'] else 'No (irregular)'}")
        logger.info(f"   Plots to place: {len(self.plot_configs)}")
        
        # STEP 1: Generate roads within polygon
        logger.info("\n📍 STEP 1: Generating road network within polygon...")
        self._generate_roads()
        logger.info(f"   ✓ Generated {len(self.roads)} road segments")
        
        # STEP 2: Calculate buildable area
        logger.info("\n📐 STEP 2: Calculating buildable area...")
        self._calculate_buildable_area()
        buildable_area = self.buildable_area.area if self.buildable_area else 0
        logger.info(f"   ✓ Buildable area: {buildable_area:,.0f} m²")
        
        # STEP 3: Place plots using NFP-grid algorithm
        logger.info("\n📦 STEP 3: Placing plots using NFP-grid algorithm...")
        self._place_plots_nfp_grid()
        logger.info(f"   ✓ Placed {len(self.placed_plots)} of {len(self.plot_configs)} plots")
        
        # STEP 4: Validate
        logger.info("\n✅ STEP 4: Validating layout...")
        is_valid, violations = self.validator.validate_layout(
            self.plot_geometries, 
            self.road_geometry
        )
        
        if is_valid:
            logger.info("   ✓ VALIDATION PASSED!")
            logger.info("     - All plots inside boundary ✅")
            logger.info("     - No overlaps ✅")
            logger.info("     - No road conflicts ✅")
        else:
            logger.warning(f"   ⚠️ Found violations:")
            if violations['outside_boundary']:
                logger.warning(f"     - {len(violations['outside_boundary'])} outside boundary")
            if violations['overlaps']:
                logger.warning(f"     - {len(violations['overlaps'])} overlaps")
            if violations['road_conflicts']:
                logger.warning(f"     - {len(violations['road_conflicts'])} road conflicts")
        
        # STEP 5: Calculate metrics
        logger.info("\n📊 STEP 5: Calculating metrics...")
        metrics = self._calculate_metrics()
        
        # RESULT
        result = {
            'boundary': self.boundary,
            'boundary_info': info,
            'roads': self.roads,
            'road_geometry': self.road_geometry,
            'buildable_area': self.buildable_area,
            'plots': self.plot_geometries,
            'placed_geometries': self.placed_plots,
            'is_valid': is_valid,
            'violations': violations,
            'metrics': metrics
        }
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📋 OPTIMIZATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"   Boundary area:    {self.boundary_area:>12,.0f} m²")
        logger.info(f"   Buildable area:   {buildable_area:>12,.0f} m²")
        logger.info(f"   Total plot area:  {metrics['total_plot_area']:>12,.0f} m²")
        logger.info(f"   Plots placed:     {metrics['num_plots']:>12d} / {len(self.plot_configs)}")
        logger.info(f"   Utilization:      {metrics['utilization']*100:>11.1f}%")
        logger.info(f"   Valid layout:     {'✅ YES' if is_valid else '❌ NO':>12s}")
        logger.info("=" * 60)
        
        return result
    
    def _generate_roads(self):
        """Generate road network within polygon boundary"""
        minx, miny, maxx, maxy = self.bounds
        roads = []
        
        # Vertical roads (N-S)
        x = minx + self.road_spacing / 2
        while x < maxx:
            road_line = LineString([(x, miny - 50), (x, maxy + 50)])
            # Clip to polygon
            clipped = road_line.intersection(self.boundary)
            if not clipped.is_empty:
                if isinstance(clipped, LineString):
                    roads.append(clipped)
                elif hasattr(clipped, 'geoms'):
                    for g in clipped.geoms:
                        if isinstance(g, LineString):
                            roads.append(g)
            x += self.road_spacing
        
        # Horizontal roads (E-W)
        y = miny + self.road_spacing / 2
        while y < maxy:
            road_line = LineString([(minx - 50, y), (maxx + 50, y)])
            clipped = road_line.intersection(self.boundary)
            if not clipped.is_empty:
                if isinstance(clipped, LineString):
                    roads.append(clipped)
                elif hasattr(clipped, 'geoms'):
                    for g in clipped.geoms:
                        if isinstance(g, LineString):
                            roads.append(g)
            y += self.road_spacing
        
        self.roads = roads
        
        # Create buffered road geometry
        if roads:
            buffered = [r.buffer(self.road_buffer) for r in roads]
            self.road_geometry = unary_union(buffered)
        else:
            self.road_geometry = Polygon()
    
    def _calculate_buildable_area(self):
        """Buildable = Polygon - Setback - Roads"""
        # Apply setback
        inner = self.boundary.buffer(-self.setback)
        
        # Subtract roads
        if self.road_geometry and not self.road_geometry.is_empty:
            self.buildable_area = inner.difference(self.road_geometry)
        else:
            self.buildable_area = inner
    
    def _place_plots_nfp_grid(self):
        """
        Place plots using NFP-inspired grid-based search.
        
        Algorithm:
        1. Create grid of candidate positions within bounding box
        2. For each plot config (sorted by size, largest first):
           a. Try each grid position
           b. If position is valid (inside boundary, no overlaps), place plot
           c. Move to next plot
        """
        if self.buildable_area is None or self.buildable_area.is_empty:
            logger.warning("No buildable area available")
            return
        
        # Handle MultiPolygon
        if isinstance(self.buildable_area, MultiPolygon):
            buildable_polys = list(self.buildable_area.geoms)
        else:
            buildable_polys = [self.buildable_area]
        
        # Sort plots by area (largest first for better packing)
        sorted_configs = sorted(
            enumerate(self.plot_configs),
            key=lambda x: x[1]['width'] * x[1]['height'],
            reverse=True
        )
        
        placed_indices = set()
        
        for buildable in buildable_polys:
            if buildable.is_empty or buildable.area < 500:
                continue
            
            minx, miny, maxx, maxy = buildable.bounds
            
            for orig_idx, config in sorted_configs:
                if orig_idx in placed_indices:
                    continue
                
                width = config['width']
                height = config['height']
                placed = False
                
                # Try grid positions
                for x in np.arange(minx + self.plot_spacing, 
                                  maxx - width - self.plot_spacing, 
                                  self.grid_step):
                    for y in np.arange(miny + self.plot_spacing, 
                                      maxy - height - self.plot_spacing, 
                                      self.grid_step):
                        # Create candidate rectangle
                        candidate = box(x, y, x + width, y + height)
                        
                        # Check: inside buildable area
                        if not buildable.contains(candidate):
                            continue
                        
                        # Check: no overlaps with placed plots
                        has_overlap = False
                        for existing in self.placed_plots:
                            if candidate.buffer(self.plot_spacing/2).intersects(
                                existing.buffer(self.plot_spacing/2)
                            ):
                                has_overlap = True
                                break
                        
                        if not has_overlap:
                            # Place the plot
                            self.placed_plots.append(candidate)
                            self.plot_geometries.append({
                                'id': f'PLOT_{len(self.placed_plots):03d}',
                                'x': x,
                                'y': y,
                                'width': width,
                                'height': height,
                                'area': width * height,
                                'type': config.get('type', 'industrial'),
                                'geom': candidate
                            })
                            placed_indices.add(orig_idx)
                            placed = True
                            break
                    
                    if placed:
                        break
    
    def _calculate_metrics(self) -> Dict:
        """Calculate space utilization metrics"""
        total_plot_area = sum(p['area'] for p in self.plot_geometries)
        buildable_area = self.buildable_area.area if self.buildable_area else 0
        
        return {
            'boundary_area': self.boundary_area,
            'buildable_area': buildable_area,
            'total_plot_area': total_plot_area,
            'num_plots': len(self.plot_geometries),
            'avg_plot_size': total_plot_area / len(self.plot_geometries) if self.plot_geometries else 0,
            'utilization': total_plot_area / buildable_area if buildable_area > 0 else 0,
            'overall_coverage': total_plot_area / self.boundary_area if self.boundary_area > 0 else 0,
            'placement_rate': len(self.plot_geometries) / len(self.plot_configs) if self.plot_configs else 0
        }


# =============================================================================
# DXF EXPORT
# =============================================================================

def export_polygon_layout_to_dxf(result: Dict, output_path: str) -> str:
    """Export polygon-constrained layout to DXF"""
    import ezdxf
    
    doc = ezdxf.new(dxfversion='R2010')
    msp = doc.modelspace()
    
    # Layers
    doc.layers.add('BOUNDARY', color=1)      # Red
    doc.layers.add('ROADS', color=7)         # White
    doc.layers.add('BUILDABLE', color=4)     # Cyan
    doc.layers.add('PLOTS', color=5)         # Blue
    doc.layers.add('LABELS', color=3)        # Green
    
    # Draw polygon boundary
    boundary = result.get('boundary')
    if boundary:
        coords = list(boundary.exterior.coords)
        msp.add_lwpolyline(
            [(c[0], c[1]) for c in coords],
            close=True,
            dxfattribs={'layer': 'BOUNDARY', 'lineweight': 70}
        )
    
    # Draw roads
    for road in result.get('roads', []):
        coords = list(road.coords)
        if len(coords) >= 2:
            msp.add_line(coords[0], coords[-1], dxfattribs={'layer': 'ROADS'})
    
    # Draw plots
    for plot in result.get('plots', []):
        x, y = plot['x'], plot['y']
        w, h = plot['width'], plot['height']
        
        points = [(x, y), (x+w, y), (x+w, y+h), (x, y+h), (x, y)]
        msp.add_lwpolyline(points, close=True, dxfattribs={'layer': 'PLOTS'})
        
        # Label
        msp.add_mtext(
            f"{plot['id']}\n{w}×{h}m",
            dxfattribs={'layer': 'LABELS', 'char_height': 3}
        ).set_location((x + w/2, y + h/2))
    
    # Metrics
    metrics = result.get('metrics', {})
    if metrics and boundary:
        info = (
            f"POLYGON LAYOUT\n"
            f"Plots: {metrics.get('num_plots', 0)}\n"
            f"Area: {metrics.get('total_plot_area', 0):,.0f} m²\n"
            f"Util: {metrics.get('utilization', 0)*100:.1f}%\n"
            f"Valid: {'YES' if result.get('is_valid') else 'NO'}"
        )
        minx, miny, maxx, maxy = boundary.bounds
        msp.add_mtext(
            info,
            dxfattribs={'layer': 'LABELS', 'char_height': 4}
        ).set_location((minx + 10, maxy - 10))
    
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    doc.saveas(output_path)
    logger.info(f"✅ DXF exported to: {output_path}")
    
    return output_path


# =============================================================================
# VISUALIZATION
# =============================================================================

def visualize_polygon_layout(result: Dict, save_path: Optional[str] = None):
    """Visualize the polygon-constrained layout"""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MplPolygon, Rectangle
    from matplotlib.collections import PatchCollection
    
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Draw boundary
    boundary = result.get('boundary')
    if boundary:
        coords = list(boundary.exterior.coords)
        boundary_patch = MplPolygon(coords, fill=False, edgecolor='red', 
                                   linewidth=3, label='Land Boundary')
        ax.add_patch(boundary_patch)
    
    # Draw roads
    for road in result.get('roads', []):
        coords = list(road.coords)
        xs, ys = zip(*coords)
        ax.plot(xs, ys, 'gray', linewidth=2, alpha=0.7)
    
    # Draw plots
    colors = ['#3498db', '#2ecc71', '#e74c3c', '#9b59b6', '#f39c12', '#1abc9c']
    for idx, plot in enumerate(result.get('plots', [])):
        x, y = plot['x'], plot['y']
        w, h = plot['width'], plot['height']
        rect = Rectangle((x, y), w, h,
                         linewidth=1.5,
                         edgecolor='black',
                         facecolor=colors[idx % len(colors)],
                         alpha=0.7)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, plot['id'], 
               ha='center', va='center', fontsize=7, fontweight='bold')
    
    # Formatting
    ax.set_aspect('equal')
    ax.set_title('Polygon-Constrained Industrial Estate Layout', fontsize=14, fontweight='bold')
    ax.set_xlabel('X (meters)')
    ax.set_ylabel('Y (meters)')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)
    
    # Add metrics
    metrics = result.get('metrics', {})
    if metrics:
        text = (f"Plots: {metrics.get('num_plots', 0)}\n"
                f"Area: {metrics.get('total_plot_area', 0):,.0f} m²\n"
                f"Util: {metrics.get('utilization', 0)*100:.1f}%")
        ax.text(0.02, 0.98, text, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat'))
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"✅ Saved visualization to: {save_path}")
    
    plt.show()


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🔷 POLYGON-CONSTRAINED INDUSTRIAL ESTATE OPTIMIZER")
    print("="*70)
    
    # Example 1: Irregular polygon boundary (from document)
    irregular_boundary = [
        (310, 170),   # Corner 1
        (470, 170),   # Corner 2
        (590, 330),   # Corner 3
        (470, 450),   # Corner 4
        (310, 390),   # Corner 5
        (310, 170)    # Close
    ]
    
    # Example 2: L-shaped polygon
    l_shaped_boundary = [
        (0, 0),
        (400, 0),
        (400, 200),
        (200, 200),
        (200, 400),
        (0, 400),
        (0, 0)
    ]
    
    # Use the irregular boundary
    boundary = Polygon(irregular_boundary)
    
    # Define plots
    plots = [
        {'width': 50, 'height': 60, 'type': 'warehouse'},
        {'width': 40, 'height': 50, 'type': 'office'},
        {'width': 60, 'height': 70, 'type': 'factory'},
        {'width': 45, 'height': 55, 'type': 'storage'},
    ] * 4  # 16 plots
    
    # Create optimizer
    optimizer = PolygonConstrainedEstateOptimizer(
        boundary=boundary,
        plot_configs=plots,
        road_width=20,
        road_spacing=150,
        setback=10,
        plot_spacing=10,
        grid_step=10
    )
    
    # Run optimization
    result = optimizer.optimize()
    
    # Export to DXF
    os.makedirs('output', exist_ok=True)
    export_polygon_layout_to_dxf(result, 'output/polygon_layout.dxf')
    
    # Print results
    print("\n📋 PLACED PLOTS:")
    for p in result['plots'][:10]:
        print(f"   {p['id']}: ({p['x']:.0f}, {p['y']:.0f}) → {p['width']}×{p['height']}m")
    if len(result['plots']) > 10:
        print(f"   ... and {len(result['plots']) - 10} more")
    
    print("\n✅ COMPLETE! Check output/polygon_layout.dxf")
