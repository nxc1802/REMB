"""
Professional Industrial Estate Planner
======================================

Follows proper industrial estate planning methodology:
1. Extract boundary from DXF
2. Apply setback buffer INSIDE boundary
3. Create main road network INSIDE the buildable area
4. Generate grid-aligned plots WITHIN the usable area
5. Ensure ALL plots are COMPLETELY INSIDE the boundary
6. Export with all data preserved

Reference: Industrial Estate Planning with Python and Geo Libraries
           by Donato_TH (Medium)
"""

import os
import sys
sys.path.insert(0, '.')

import numpy as np
import ezdxf
from shapely.geometry import Polygon, LineString, box, MultiPolygon
from shapely.ops import unary_union, split
from shapely.affinity import scale as scale_geom, rotate
from shapely.validation import make_valid
from typing import List, Dict, Tuple, Optional
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IndustrialEstatePlanner:
    """
    Professional industrial estate layout planner.
    
    Correct order of operations:
    1. Read boundary from DXF
    2. Apply setback (buffer inward)
    3. Create main road network
    4. Calculate buildable zones (usable area minus roads)
    5. Generate grid-aligned plots INSIDE buildable zones
    6. Validate all plots are inside boundary
    7. Export with data preservation
    """
    
    def __init__(self, dxf_path: str):
        """Initialize with DXF file"""
        self.dxf_path = dxf_path
        self.doc = None
        self.msp = None
        
        # Geometry
        self.boundary_raw = None  # Original boundary in DXF units
        self.boundary_m = None    # Boundary in meters
        self.setback_zone = None  # Buildable area after setback
        self.roads = []           # Road geometries
        self.road_buffer = None   # Union of all road buffers
        self.usable_area = None   # Area for plots (setback - roads)
        self.plots = []           # Final plots
        
        # Parameters
        self.unit_scale = 0.001   # Default mm to m
        self.setback_distance = 3.0  # meters
        self.road_width = 6.0      # meters
        self.min_plot_width = 8.0  # meters
        self.min_plot_height = 10.0 # meters
        self.plot_spacing = 2.0    # meters between plots
        
        # Load DXF
        self._load_dxf()
    
    def _load_dxf(self):
        """Load DXF file"""
        try:
            self.doc = ezdxf.readfile(self.dxf_path)
            self.msp = self.doc.modelspace()
            logger.info(f"Loaded: {self.dxf_path}")
            
            # Get file size
            size_kb = os.path.getsize(self.dxf_path) / 1024
            logger.info(f"Size: {size_kb:.1f} KB")
            
            # Count entities
            entity_count = len(list(self.msp))
            logger.info(f"Entities: {entity_count}")
            
        except Exception as e:
            logger.error(f"Error loading DXF: {e}")
    
    def extract_boundary(self) -> Optional[Polygon]:
        """Extract main boundary polygon from DXF"""
        candidates = []
        
        for entity in self.msp.query('LWPOLYLINE'):
            coords = [(p[0], p[1]) for p in entity.get_points('xy')]
            if len(coords) >= 3:
                # Close polygon if not closed
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                try:
                    poly = Polygon(coords)
                    if not poly.is_valid:
                        poly = make_valid(poly)
                    if poly.is_valid and poly.area > 1000:
                        candidates.append({
                            'polygon': poly,
                            'area': poly.area,
                            'layer': entity.dxf.layer
                        })
                except:
                    pass
        
        if candidates:
            # Get largest polygon (usually the main boundary)
            best = max(candidates, key=lambda x: x['area'])
            self.boundary_raw = best['polygon']
            
            # Detect units and convert to meters
            max_coord = max(abs(c) for c in self.boundary_raw.bounds)
            if max_coord > 10000:
                self.unit_scale = 0.001  # mm to m
                logger.info("Detected: Millimeters -> converting to meters")
            else:
                self.unit_scale = 1.0  # Already in meters
                logger.info("Detected: Meters")
            
            # Convert to meters
            self.boundary_m = scale_geom(
                self.boundary_raw, 
                xfact=self.unit_scale, 
                yfact=self.unit_scale, 
                origin=(0, 0)
            )
            
            logger.info(f"Boundary extracted: {self.boundary_m.area:.2f} m²")
            return self.boundary_m
        
        logger.error("No boundary found in DXF")
        return None
    
    def apply_setback(self, distance: float = None) -> Optional[Polygon]:
        """
        Apply setback by buffering INWARD (negative buffer).
        This creates the buildable zone inside the boundary.
        """
        if self.boundary_m is None:
            logger.error("No boundary to apply setback to")
            return None
        
        if distance is not None:
            self.setback_distance = distance
        
        # Buffer inward (negative distance)
        self.setback_zone = self.boundary_m.buffer(-self.setback_distance)
        
        if self.setback_zone.is_empty:
            logger.warning("Setback too large - using smaller value")
            self.setback_distance = self.setback_distance / 2
            self.setback_zone = self.boundary_m.buffer(-self.setback_distance)
        
        if not self.setback_zone.is_empty:
            logger.info(f"Setback applied: {self.setback_distance}m")
            logger.info(f"Buildable area: {self.setback_zone.area:.2f} m²")
        
        return self.setback_zone
    
    def create_main_road(self) -> List[Polygon]:
        """
        Create main road through the center of the land.
        Road runs from edge to edge for access.
        """
        if self.setback_zone is None:
            self.apply_setback()
        
        minx, miny, maxx, maxy = self.setback_zone.bounds
        center_x = (minx + maxx) / 2
        center_y = (miny + maxy) / 2
        
        self.roads = []
        
        # Create diagonal main road (like in the reference image)
        # Calculate the longest diagonal
        width = maxx - minx
        height = maxy - miny
        
        if width > height:
            # Horizontal-ish main road
            road_line = LineString([
                (minx - 10, center_y),
                (maxx + 10, center_y)
            ])
        else:
            # Vertical-ish main road
            road_line = LineString([
                (center_x, miny - 10),
                (center_x, maxy + 10)
            ])
        
        # Clip road to boundary and buffer
        road_clipped = road_line.intersection(self.setback_zone)
        if not road_clipped.is_empty:
            road_buffer = road_clipped.buffer(self.road_width / 2)
            self.roads.append({
                'line': road_clipped,
                'buffer': road_buffer,
                'type': 'main'
            })
        
        # Create road buffer union
        if self.roads:
            self.road_buffer = unary_union([r['buffer'] for r in self.roads])
            logger.info(f"Main road created: {self.road_width}m wide")
        
        return self.roads
    
    def calculate_usable_area(self) -> Polygon:
        """
        Calculate remaining usable area after roads.
        Usable = Setback zone - Road buffers
        """
        if self.setback_zone is None:
            self.apply_setback()
        
        if self.road_buffer is not None and not self.road_buffer.is_empty:
            self.usable_area = self.setback_zone.difference(self.road_buffer)
        else:
            self.usable_area = self.setback_zone
        
        # Handle MultiPolygon
        if isinstance(self.usable_area, MultiPolygon):
            logger.info(f"Usable area split into {len(self.usable_area.geoms)} zones")
        else:
            logger.info(f"Usable area: {self.usable_area.area:.2f} m²")
        
        return self.usable_area
    
    def generate_plots_grid(self) -> List[Dict]:
        """
        Generate plots using grid-based placement.
        ALL plots must be COMPLETELY INSIDE the usable area.
        """
        if self.usable_area is None:
            self.calculate_usable_area()
        
        self.plots = []
        plot_id = 1
        
        # Handle MultiPolygon
        if isinstance(self.usable_area, MultiPolygon):
            zones = list(self.usable_area.geoms)
        else:
            zones = [self.usable_area]
        
        for zone_idx, zone in enumerate(zones):
            if zone.is_empty or zone.area < 50:
                continue
            
            minx, miny, maxx, maxy = zone.bounds
            
            # Grid-based placement
            x = minx + self.plot_spacing
            while x + self.min_plot_width < maxx - self.plot_spacing:
                y = miny + self.plot_spacing
                while y + self.min_plot_height < maxy - self.plot_spacing:
                    # Create candidate plot
                    plot_box = box(x, y, x + self.min_plot_width, y + self.min_plot_height)
                    
                    # CRITICAL: Check if plot is COMPLETELY INSIDE the zone
                    if zone.contains(plot_box):
                        # Check no overlap with existing plots
                        overlaps = False
                        for existing in self.plots:
                            if plot_box.buffer(self.plot_spacing/2).intersects(
                                existing['geom'].buffer(self.plot_spacing/2)
                            ):
                                overlaps = True
                                break
                        
                        if not overlaps:
                            self.plots.append({
                                'id': f'PLOT_{plot_id:03d}',
                                'x': x,
                                'y': y,
                                'width': self.min_plot_width,
                                'height': self.min_plot_height,
                                'area': self.min_plot_width * self.min_plot_height,
                                'zone': zone_idx,
                                'geom': plot_box
                            })
                            plot_id += 1
                    
                    y += self.min_plot_height + self.plot_spacing
                x += self.min_plot_width + self.plot_spacing
        
        logger.info(f"Generated {len(self.plots)} plots")
        return self.plots
    
    def validate_layout(self) -> Tuple[bool, Dict]:
        """
        Validate that all plots are inside boundary and don't overlap.
        """
        violations = {
            'outside_boundary': [],
            'outside_setback': [],
            'overlapping': [],
            'on_road': []
        }
        
        for i, plot in enumerate(self.plots):
            geom = plot['geom']
            
            # Check inside main boundary
            if not self.boundary_m.contains(geom):
                violations['outside_boundary'].append(plot['id'])
            
            # Check inside setback zone
            if self.setback_zone and not self.setback_zone.contains(geom):
                violations['outside_setback'].append(plot['id'])
            
            # Check not on road
            if self.road_buffer and geom.intersects(self.road_buffer):
                violations['on_road'].append(plot['id'])
            
            # Check overlaps
            for j in range(i + 1, len(self.plots)):
                other = self.plots[j]['geom']
                if geom.intersects(other):
                    violations['overlapping'].append((plot['id'], self.plots[j]['id']))
        
        is_valid = all(len(v) == 0 for v in violations.values())
        
        if is_valid:
            logger.info("Validation PASSED - all plots inside boundary")
        else:
            logger.warning(f"Validation issues: {violations}")
        
        return is_valid, violations
    
    def get_metrics(self) -> Dict:
        """Calculate layout metrics"""
        total_plot_area = sum(p['area'] for p in self.plots)
        boundary_area = self.boundary_m.area if self.boundary_m else 0
        usable_area = self.usable_area.area if self.usable_area else 0
        
        return {
            'boundary_area': boundary_area,
            'setback_area': self.setback_zone.area if self.setback_zone else 0,
            'usable_area': usable_area,
            'total_plot_area': total_plot_area,
            'num_plots': len(self.plots),
            'utilization': (total_plot_area / usable_area * 100) if usable_area > 0 else 0,
            'boundary_utilization': (total_plot_area / boundary_area * 100) if boundary_area > 0 else 0
        }
    
    def export_dxf_with_preservation(self, output_path: str) -> bool:
        """
        Export optimized layout with ALL original data preserved.
        """
        if self.doc is None:
            logger.error("No document loaded")
            return False
        
        # Create new layers for optimization results
        layer_colors = {
            'ESTATE_SETBACK': 4,      # Cyan
            'ESTATE_ROADS': 7,        # White
            'ESTATE_PLOTS': 5,        # Blue
            'ESTATE_LABELS': 3,       # Green
            'ESTATE_METADATA': 2      # Yellow
        }
        
        for layer_name, color in layer_colors.items():
            if layer_name not in self.doc.layers:
                self.doc.layers.add(layer_name, color=color)
        
        # Scale factor to convert back to DXF units
        scale = 1.0 / self.unit_scale if self.unit_scale != 0 else 1.0
        
        # Draw setback boundary
        if self.setback_zone and not self.setback_zone.is_empty:
            coords = [(c[0] * scale, c[1] * scale) for c in self.setback_zone.exterior.coords]
            self.msp.add_lwpolyline(
                coords, close=True,
                dxfattribs={'layer': 'ESTATE_SETBACK', 'color': 4}
            )
        
        # Draw roads
        for road in self.roads:
            if 'line' in road and not road['line'].is_empty:
                coords = [(c[0] * scale, c[1] * scale) for c in road['line'].coords]
                self.msp.add_lwpolyline(
                    coords,
                    dxfattribs={'layer': 'ESTATE_ROADS', 'color': 30, 'lineweight': 50}
                )
        
        # Draw plots
        for plot in self.plots:
            x, y = plot['x'] * scale, plot['y'] * scale
            w, h = plot['width'] * scale, plot['height'] * scale
            
            points = [(x, y), (x+w, y), (x+w, y+h), (x, y+h)]
            self.msp.add_lwpolyline(
                points, close=True,
                dxfattribs={'layer': 'ESTATE_PLOTS', 'color': 5}
            )
            
            # Add label
            label_size = min(w, h) / 8
            self.msp.add_mtext(
                f"{plot['id']}\n{plot['width']:.0f}x{plot['height']:.0f}m",
                dxfattribs={'layer': 'ESTATE_LABELS', 'char_height': label_size}
            ).set_location((x + w/2, y + h/2))
        
        # Add metrics text
        metrics = self.get_metrics()
        if self.boundary_m:
            minx, miny, maxx, maxy = self.boundary_m.bounds
            info_text = (
                f"ESTATE LAYOUT\n"
                f"Boundary: {metrics['boundary_area']:.0f} m²\n"
                f"Plots: {metrics['num_plots']}\n"
                f"Plot Area: {metrics['total_plot_area']:.0f} m²\n"
                f"Utilization: {metrics['utilization']:.1f}%\n"
                f"Date: {datetime.now().strftime('%Y-%m-%d')}"
            )
            self.msp.add_mtext(
                info_text,
                dxfattribs={'layer': 'ESTATE_METADATA', 'char_height': 500}
            ).set_location(((minx + 500) * scale, (maxy + 500) * scale))
        
        # Save
        self.doc.saveas(output_path)
        
        # Verify
        input_size = os.path.getsize(self.dxf_path) / 1024
        output_size = os.path.getsize(output_path) / 1024
        
        logger.info(f"Exported: {output_path}")
        logger.info(f"Input: {input_size:.1f} KB -> Output: {output_size:.1f} KB")
        logger.info(f"Preservation: {(output_size/input_size)*100:.1f}%")
        
        return True
    
    def plan_estate(self, output_path: str = None) -> Dict:
        """
        Execute complete estate planning pipeline.
        """
        print("\n" + "=" * 70)
        print("INDUSTRIAL ESTATE PLANNER")
        print("=" * 70)
        
        # Step 1: Extract boundary
        print("\nStep 1: Extracting boundary from DXF...")
        boundary = self.extract_boundary()
        if boundary is None:
            return {'status': 'ERROR', 'message': 'No boundary found'}
        print(f"  ✓ Boundary: {boundary.area:.2f} m²")
        
        # Step 2: Apply setback
        print("\nStep 2: Applying setback buffer...")
        setback = self.apply_setback(self.setback_distance)
        print(f"  ✓ Setback: {self.setback_distance}m inward")
        print(f"  ✓ Buildable zone: {setback.area:.2f} m²")
        
        # Step 3: Create roads
        print("\nStep 3: Creating main road network...")
        roads = self.create_main_road()
        print(f"  ✓ Roads: {len(roads)} segments")
        
        # Step 4: Calculate usable area
        print("\nStep 4: Calculating usable area...")
        usable = self.calculate_usable_area()
        if isinstance(usable, MultiPolygon):
            print(f"  ✓ Usable zones: {len(usable.geoms)}")
        else:
            print(f"  ✓ Usable area: {usable.area:.2f} m²")
        
        # Step 5: Generate plots
        print("\nStep 5: Generating plot grid...")
        plots = self.generate_plots_grid()
        print(f"  ✓ Plots generated: {len(plots)}")
        
        # Step 6: Validate
        print("\nStep 6: Validating layout...")
        is_valid, violations = self.validate_layout()
        print(f"  ✓ Valid: {is_valid}")
        if violations['outside_boundary']:
            print(f"  ⚠ Outside boundary: {len(violations['outside_boundary'])}")
        
        # Step 7: Calculate metrics
        print("\nStep 7: Calculating metrics...")
        metrics = self.get_metrics()
        print(f"  ✓ Total plots: {metrics['num_plots']}")
        print(f"  ✓ Plot area: {metrics['total_plot_area']:.2f} m²")
        print(f"  ✓ Utilization: {metrics['utilization']:.1f}%")
        
        # Step 8: Export
        if output_path is None:
            base, ext = os.path.splitext(self.dxf_path)
            output_path = os.path.join('output', os.path.basename(base) + '_ESTATE.dxf')
        
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        print(f"\nStep 8: Exporting with data preservation...")
        self.export_dxf_with_preservation(output_path)
        print(f"  ✓ Output: {output_path}")
        
        # Summary
        print("\n" + "=" * 70)
        print("PLANNING COMPLETE")
        print("=" * 70)
        
        return {
            'status': 'SUCCESS',
            'input': self.dxf_path,
            'output': output_path,
            'metrics': metrics,
            'is_valid': is_valid,
            'violations': violations
        }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    input_file = r"D:\Gitrepo\REMB\examples\Lot Plan Bel air Technical Description.dxf"
    output_file = r"D:\Gitrepo\REMB\output\Bel_Air_ESTATE_PLAN.dxf"
    
    planner = IndustrialEstatePlanner(input_file)
    
    # Configure for small parcel
    planner.setback_distance = 2.0  # 2m setback
    planner.road_width = 4.0        # 4m road
    planner.min_plot_width = 6.0    # 6m plot width
    planner.min_plot_height = 8.0   # 8m plot height
    planner.plot_spacing = 1.0      # 1m between plots
    
    result = planner.plan_estate(output_file)
    
    if result['status'] == 'SUCCESS':
        print(f"\n✓ Estate planned successfully!")
        print(f"  Plots: {result['metrics']['num_plots']}")
        print(f"  Utilization: {result['metrics']['utilization']:.1f}%")
    else:
        print(f"\n✗ Error: {result.get('message', 'Unknown')}")
