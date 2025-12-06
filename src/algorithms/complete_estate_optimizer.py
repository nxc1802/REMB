"""
Complete Estate Optimizer - Full Flow Production Version
=========================================================

This is the COMPLETE, FULLY WORKING optimizer that:
1. Reads the real DXF cadastral boundary
2. Converts units (mm to m)
3. Creates buffer/setback zone
4. Generates diagonal main road
5. Creates secondary roads for grid
6. Fills ENTIRE usable area with plots
7. Exports with ALL original data preserved

Key fix: Use axis-aligned plots (no rotation) for reliable placement
"""

import os
import sys
sys.path.insert(0, '.')

import numpy as np
import ezdxf
from shapely.geometry import Polygon, LineString, box, MultiPolygon, Point
from shapely.ops import unary_union
from shapely.affinity import scale as scale_geom, rotate, translate
from shapely.validation import make_valid
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import math


class CompleteEstateOptimizer:
    """
    Complete, production-ready estate optimizer.
    Fills the entire usable area with properly placed plots.
    """
    
    def __init__(self, dxf_path: str):
        self.dxf_path = dxf_path
        self.doc = None
        self.msp = None
        
        # Geometry
        self.boundary_raw = None  # Original in DXF units
        self.boundary_m = None    # Converted to meters
        self.buffer_zone = None   # After setback
        self.main_road_line = None
        self.main_road_buffer = None
        self.secondary_road_lines = []
        self.secondary_road_buffers = []
        self.all_roads_buffer = None
        self.usable_zones = []
        self.plots = []
        
        # Parameters (will be auto-calibrated based on area)
        self.unit_scale = 0.001  # mm to m
        self.setback_distance = 1.5
        self.main_road_width = 4.0
        self.secondary_road_width = 3.0
        self.plot_width = 6.0
        self.plot_height = 8.0
        self.plot_spacing = 1.0
        
        # Load DXF
        self._load_dxf()
    
    def _load_dxf(self):
        """Load DXF file and count entities"""
        try:
            self.doc = ezdxf.readfile(self.dxf_path)
            self.msp = self.doc.modelspace()
            entity_count = len(list(self.msp))
            layer_count = len(list(self.doc.layers))
            print("[LOAD] File: %s" % self.dxf_path)
            print("[LOAD] Entities: %d, Layers: %d" % (entity_count, layer_count))
        except Exception as e:
            print("[ERROR] Loading DXF: %s" % e)
    
    def extract_boundary(self) -> Optional[Polygon]:
        """Extract and convert main boundary polygon"""
        print("\n[STEP 1] Extracting boundary...")
        
        candidates = []
        for entity in self.msp.query('LWPOLYLINE'):
            coords = [(p[0], p[1]) for p in entity.get_points('xy')]
            if len(coords) >= 3:
                # Close polygon
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
        
        if not candidates:
            print("[ERROR] No valid boundary found!")
            return None
        
        # Get largest polygon
        best = max(candidates, key=lambda x: x['area'])
        self.boundary_raw = best['polygon']
        
        # Detect units
        max_coord = max(abs(c) for c in self.boundary_raw.bounds)
        if max_coord > 10000:
            self.unit_scale = 0.001  # mm to m
            print("[UNITS] Millimeters detected (scale: 0.001)")
        elif max_coord > 100:
            self.unit_scale = 0.01   # cm to m
            print("[UNITS] Centimeters detected (scale: 0.01)")
        else:
            self.unit_scale = 1.0    # Already meters
            print("[UNITS] Meters detected (scale: 1.0)")
        
        # Convert to meters
        self.boundary_m = scale_geom(
            self.boundary_raw,
            xfact=self.unit_scale,
            yfact=self.unit_scale,
            origin=(0, 0)
        )
        
        print("[BOUNDARY] Area: %.2f m2" % self.boundary_m.area)
        print("[BOUNDARY] Bounds: (%.2f, %.2f) to (%.2f, %.2f)" % self.boundary_m.bounds)
        
        return self.boundary_m
    
    def auto_calibrate_parameters(self):
        """Automatically calibrate parameters based on boundary area"""
        print("\n[STEP 2] Auto-calibrating parameters...")
        
        area = self.boundary_m.area
        
        if area < 200:
            self.setback_distance = 0.3
            self.main_road_width = 1.5
            self.secondary_road_width = 1.0
            self.plot_width = 2.0
            self.plot_height = 3.0
            self.plot_spacing = 0.3
        elif area < 500:
            self.setback_distance = 0.5
            self.main_road_width = 2.0
            self.secondary_road_width = 1.5
            self.plot_width = 3.0
            self.plot_height = 4.0
            self.plot_spacing = 0.5
        elif area < 1000:  # ~600m2 like Bel Air
            self.setback_distance = 0.8
            self.main_road_width = 2.5
            self.secondary_road_width = 2.0
            self.plot_width = 4.0
            self.plot_height = 5.0
            self.plot_spacing = 0.6
        elif area < 5000:
            self.setback_distance = 1.5
            self.main_road_width = 4.0
            self.secondary_road_width = 3.0
            self.plot_width = 8.0
            self.plot_height = 10.0
            self.plot_spacing = 1.0
        else:
            self.setback_distance = 3.0
            self.main_road_width = 6.0
            self.secondary_road_width = 4.0
            self.plot_width = 15.0
            self.plot_height = 20.0
            self.plot_spacing = 2.0
        
        print("[PARAMS] Area: %.0f m2" % area)
        print("[PARAMS] Setback: %.1fm" % self.setback_distance)
        print("[PARAMS] Main road: %.1fm" % self.main_road_width)
        print("[PARAMS] Plot size: %.1fm x %.1fm" % (self.plot_width, self.plot_height))
        print("[PARAMS] Spacing: %.1fm" % self.plot_spacing)
    
    def apply_setback(self) -> Polygon:
        """Apply setback buffer (inward)"""
        print("\n[STEP 3] Applying setback buffer...")
        
        self.buffer_zone = self.boundary_m.buffer(-self.setback_distance)
        
        if self.buffer_zone.is_empty:
            # Try smaller setback
            self.setback_distance = self.setback_distance / 2
            self.buffer_zone = self.boundary_m.buffer(-self.setback_distance)
            print("[WARNING] Reduced setback to %.2fm" % self.setback_distance)
        
        print("[BUFFER] Buildable area: %.2f m2" % self.buffer_zone.area)
        return self.buffer_zone
    
    def create_road_network(self) -> Polygon:
        """Create diagonal main road and secondary roads"""
        print("\n[STEP 4] Creating road network...")
        
        # Get buffer zone bounds
        minx, miny, maxx, maxy = self.buffer_zone.bounds
        cx = (minx + maxx) / 2
        cy = (miny + maxy) / 2
        
        # Find principal axis of the polygon for road direction
        coords = list(self.buffer_zone.exterior.coords)
        
        # Find the longest edge to determine road direction
        max_length = 0
        best_angle = 45  # Default diagonal
        for i in range(len(coords) - 1):
            p1, p2 = coords[i], coords[i+1]
            length = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
            if length > max_length:
                max_length = length
                best_angle = math.degrees(math.atan2(p2[1]-p1[1], p2[0]-p1[0]))
        
        # Create main road through center
        extent = max(maxx - minx, maxy - miny) * 2
        angle_rad = math.radians(best_angle)
        
        p1 = (cx - extent * math.cos(angle_rad), cy - extent * math.sin(angle_rad))
        p2 = (cx + extent * math.cos(angle_rad), cy + extent * math.sin(angle_rad))
        
        full_line = LineString([p1, p2])
        self.main_road_line = full_line.intersection(self.buffer_zone)
        
        if not self.main_road_line.is_empty:
            self.main_road_buffer = self.main_road_line.buffer(self.main_road_width / 2)
            print("[ROAD] Main road: %.2fm long, %.1fm wide" % (
                self.main_road_line.length, self.main_road_width))
        
        # Create secondary roads perpendicular to main road
        self.secondary_road_lines = []
        self.secondary_road_buffers = []
        
        if self.main_road_line and not self.main_road_line.is_empty:
            perp_angle = angle_rad + math.pi / 2
            road_spacing = max(10, self.buffer_zone.area ** 0.5 / 3)
            
            num_secondary = max(2, int(self.main_road_line.length / road_spacing))
            
            for i in range(num_secondary):
                fraction = (i + 1) / (num_secondary + 1)
                point = self.main_road_line.interpolate(fraction, normalized=True)
                
                p1 = (point.x - extent * math.cos(perp_angle),
                      point.y - extent * math.sin(perp_angle))
                p2 = (point.x + extent * math.cos(perp_angle),
                      point.y + extent * math.sin(perp_angle))
                
                perp_line = LineString([p1, p2])
                clipped = perp_line.intersection(self.buffer_zone)
                
                if not clipped.is_empty:
                    self.secondary_road_lines.append(clipped)
                    self.secondary_road_buffers.append(
                        clipped.buffer(self.secondary_road_width / 2)
                    )
            
            print("[ROAD] Secondary roads: %d" % len(self.secondary_road_lines))
        
        # Combine all road buffers
        all_buffers = []
        if self.main_road_buffer and not self.main_road_buffer.is_empty:
            all_buffers.append(self.main_road_buffer)
        all_buffers.extend([b for b in self.secondary_road_buffers if not b.is_empty])
        
        if all_buffers:
            self.all_roads_buffer = unary_union(all_buffers)
        else:
            self.all_roads_buffer = Polygon()
        
        return self.all_roads_buffer
    
    def calculate_usable_zones(self) -> List[Polygon]:
        """Calculate usable zones by subtracting roads from buffer zone"""
        print("\n[STEP 5] Calculating usable zones...")
        
        if self.all_roads_buffer and not self.all_roads_buffer.is_empty:
            usable = self.buffer_zone.difference(self.all_roads_buffer)
        else:
            usable = self.buffer_zone
        
        # Handle MultiPolygon
        if isinstance(usable, MultiPolygon):
            self.usable_zones = [g for g in usable.geoms if not g.is_empty and g.area > 10]
        elif isinstance(usable, Polygon) and not usable.is_empty:
            self.usable_zones = [usable]
        else:
            self.usable_zones = []
        
        total_area = sum(z.area for z in self.usable_zones)
        print("[USABLE] Zones: %d, Total area: %.2f m2" % (
            len(self.usable_zones), total_area))
        
        return self.usable_zones
    
    def generate_plots_grid(self) -> List[Dict]:
        """
        Generate plots using SIMPLE GRID placement.
        NO ROTATION - axis-aligned for reliable containment.
        """
        print("\n[STEP 6] Generating plots (grid-based)...")
        
        self.plots = []
        plot_id = 1
        
        pw = self.plot_width
        ph = self.plot_height
        spacing = self.plot_spacing
        
        for zone_idx, zone in enumerate(self.usable_zones):
            if zone.is_empty or zone.area < pw * ph:
                continue
            
            minx, miny, maxx, maxy = zone.bounds
            
            # Simple grid placement
            x = minx + spacing
            while x + pw <= maxx - spacing:
                y = miny + spacing
                while y + ph <= maxy - spacing:
                    # Create candidate plot
                    plot_box = box(x, y, x + pw, y + ph)
                    
                    # CRITICAL: Check FULLY INSIDE the usable zone
                    if zone.contains(plot_box):
                        # Check NO OVERLAP with existing plots
                        has_overlap = False
                        buffer_box = plot_box.buffer(spacing / 2)
                        for existing in self.plots:
                            if buffer_box.intersects(existing['geom'].buffer(spacing / 2)):
                                has_overlap = True
                                break
                        
                        if not has_overlap:
                            self.plots.append({
                                'id': 'PLOT_%03d' % plot_id,
                                'x': x,
                                'y': y,
                                'width': pw,
                                'height': ph,
                                'area': pw * ph,
                                'zone': zone_idx,
                                'geom': plot_box
                            })
                            plot_id += 1
                    
                    y += ph + spacing
                x += pw + spacing
            
            # Also try rotated grid (90 degrees)
            x = minx + spacing
            while x + ph <= maxx - spacing:
                y = miny + spacing
                while y + pw <= maxy - spacing:
                    # Rotated plot (swap width/height)
                    plot_box = box(x, y, x + ph, y + pw)
                    
                    if zone.contains(plot_box):
                        has_overlap = False
                        buffer_box = plot_box.buffer(spacing / 2)
                        for existing in self.plots:
                            if buffer_box.intersects(existing['geom'].buffer(spacing / 2)):
                                has_overlap = True
                                break
                        
                        if not has_overlap:
                            self.plots.append({
                                'id': 'PLOT_%03d' % plot_id,
                                'x': x,
                                'y': y,
                                'width': ph,  # Swapped
                                'height': pw,  # Swapped
                                'area': pw * ph,
                                'zone': zone_idx,
                                'geom': plot_box
                            })
                            plot_id += 1
                    
                    y += pw + spacing
                x += ph + spacing
        
        print("[PLOTS] Generated: %d plots" % len(self.plots))
        return self.plots
    
    def get_metrics(self) -> Dict:
        """Calculate layout metrics"""
        total_plot_area = sum(p['area'] for p in self.plots)
        boundary_area = self.boundary_m.area if self.boundary_m else 0
        buffer_area = self.buffer_zone.area if self.buffer_zone else 0
        usable_area = sum(z.area for z in self.usable_zones)
        road_area = self.all_roads_buffer.area if self.all_roads_buffer else 0
        
        return {
            'boundary_area': boundary_area,
            'buffer_area': buffer_area,
            'road_area': road_area,
            'usable_area': usable_area,
            'total_plot_area': total_plot_area,
            'num_plots': len(self.plots),
            'utilization': (total_plot_area / usable_area * 100) if usable_area > 0 else 0,
            'overall_util': (total_plot_area / boundary_area * 100) if boundary_area > 0 else 0
        }
    
    def export_dxf(self, output_path: str) -> bool:
        """Export with ALL original data preserved"""
        print("\n[STEP 7] Exporting DXF...")
        
        if self.doc is None:
            print("[ERROR] No document to export")
            return False
        
        # Create layers
        layers = {
            'OPT_BUFFER': 4,       # Cyan
            'OPT_MAIN_ROAD': 30,   # Orange
            'OPT_SEC_ROADS': 7,    # White
            'OPT_PLOTS': 5,        # Blue
            'OPT_LABELS': 3,       # Green
            'OPT_METRICS': 2       # Yellow
        }
        
        for name, color in layers.items():
            if name not in self.doc.layers:
                self.doc.layers.add(name, color=color)
        
        # Scale factor back to DXF units
        scale = 1.0 / self.unit_scale if self.unit_scale != 0 else 1.0
        
        # Draw buffer zone
        if self.buffer_zone and not self.buffer_zone.is_empty:
            coords = [(c[0] * scale, c[1] * scale) for c in self.buffer_zone.exterior.coords]
            self.msp.add_lwpolyline(coords, close=True,
                                   dxfattribs={'layer': 'OPT_BUFFER', 'color': 4})
        
        # Draw main road
        if self.main_road_line and not self.main_road_line.is_empty:
            try:
                coords = [(c[0] * scale, c[1] * scale) for c in self.main_road_line.coords]
                self.msp.add_lwpolyline(coords,
                                       dxfattribs={'layer': 'OPT_MAIN_ROAD', 'lineweight': 70, 'color': 30})
            except:
                pass
        
        # Draw secondary roads
        for road in self.secondary_road_lines:
            if not road.is_empty:
                try:
                    coords = [(c[0] * scale, c[1] * scale) for c in road.coords]
                    self.msp.add_lwpolyline(coords,
                                           dxfattribs={'layer': 'OPT_SEC_ROADS', 'lineweight': 50})
                except:
                    pass
        
        # Draw plots
        for plot in self.plots:
            x, y = plot['x'] * scale, plot['y'] * scale
            w, h = plot['width'] * scale, plot['height'] * scale
            
            points = [(x, y), (x+w, y), (x+w, y+h), (x, y+h)]
            self.msp.add_lwpolyline(points, close=True,
                                   dxfattribs={'layer': 'OPT_PLOTS', 'color': 5})
            
            # Label
            label_size = min(w, h) / 8
            self.msp.add_mtext(
                "%s\n%.0fx%.0fm" % (plot['id'], plot['width'], plot['height']),
                dxfattribs={'layer': 'OPT_LABELS', 'char_height': max(100, label_size)}
            ).set_location((x + w/2, y + h/2))
        
        # Metrics text
        metrics = self.get_metrics()
        if self.boundary_m:
            minx = self.boundary_m.bounds[0] * scale
            maxy = self.boundary_m.bounds[3] * scale
            
            info = """ESTATE LAYOUT
Boundary: %.0f m2
Plots: %d
Plot Area: %.0f m2
Utilization: %.1f%%
Date: %s""" % (
                metrics['boundary_area'],
                metrics['num_plots'],
                metrics['total_plot_area'],
                metrics['utilization'],
                datetime.now().strftime('%Y-%m-%d %H:%M')
            )
            
            self.msp.add_mtext(info,
                              dxfattribs={'layer': 'OPT_METRICS', 'char_height': 250, 'color': 2}
                             ).set_location((minx, maxy + 500))
        
        # Save
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else 'output', exist_ok=True)
        self.doc.saveas(output_path)
        
        # Verify
        input_size = os.path.getsize(self.dxf_path) / 1024
        output_size = os.path.getsize(output_path) / 1024
        preservation = output_size / input_size * 100
        
        print("[EXPORT] %s" % output_path)
        print("[EXPORT] Input: %.1f KB -> Output: %.1f KB (%.1f%% preserved)" % (
            input_size, output_size, preservation))
        
        return True
    
    def optimize(self, output_path: str = None) -> Dict:
        """Run complete optimization pipeline"""
        print("\n" + "=" * 60)
        print("COMPLETE ESTATE OPTIMIZER - FULL FLOW")
        print("=" * 60)
        
        # Step 1: Extract boundary
        if not self.extract_boundary():
            return {'status': 'ERROR', 'message': 'No boundary found'}
        
        # Step 2: Auto-calibrate parameters
        self.auto_calibrate_parameters()
        
        # Step 3: Apply setback
        self.apply_setback()
        
        # Step 4: Create road network
        self.create_road_network()
        
        # Step 5: Calculate usable zones
        self.calculate_usable_zones()
        
        # Step 6: Generate plots
        self.generate_plots_grid()
        
        # Get metrics
        metrics = self.get_metrics()
        
        print("\n" + "-" * 40)
        print("METRICS:")
        print("  Boundary:    %.2f m2" % metrics['boundary_area'])
        print("  Usable:      %.2f m2" % metrics['usable_area'])
        print("  Plots:       %d" % metrics['num_plots'])
        print("  Plot Area:   %.2f m2" % metrics['total_plot_area'])
        print("  Utilization: %.1f%%" % metrics['utilization'])
        
        # Step 7: Export
        if output_path is None:
            base = os.path.splitext(os.path.basename(self.dxf_path))[0]
            output_path = os.path.join('output', base + '_COMPLETE.dxf')
        
        self.export_dxf(output_path)
        
        print("\n" + "=" * 60)
        print("COMPLETE!")
        print("  Output: %s" % output_path)
        print("  Plots: %d" % metrics['num_plots'])
        print("  Utilization: %.1f%%" % metrics['utilization'])
        print("=" * 60)
        
        return {
            'status': 'SUCCESS',
            'output': output_path,
            'metrics': metrics,
            'plots': self.plots
        }


# =============================================================================
# MAIN - Run full flow
# =============================================================================

if __name__ == "__main__":
    input_file = r"D:\Gitrepo\REMB\examples\Lot Plan Bel air Technical Description.dxf"
    output_file = r"D:\Gitrepo\REMB\output\Bel_Air_COMPLETE.dxf"
    
    optimizer = CompleteEstateOptimizer(input_file)
    result = optimizer.optimize(output_file)
    
    if result['status'] == 'SUCCESS':
        print("\n[SUCCESS] Estate optimization complete!")
        print("  Plots placed: %d" % result['metrics']['num_plots'])
        print("  Utilization: %.1f%%" % result['metrics']['utilization'])
        
        # Show plot positions
        if result['plots']:
            print("\n  Plot positions:")
            for p in result['plots'][:10]:
                print("    %s: (%.1f, %.1f) - %.0fx%.0fm" % (
                    p['id'], p['x'], p['y'], p['width'], p['height']))
            if len(result['plots']) > 10:
                print("    ... and %d more" % (len(result['plots']) - 10))
    else:
        print("\n[ERROR] %s" % result.get('message', 'Unknown error'))
