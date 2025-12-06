# Debug the estate planner step by step
import sys
sys.path.insert(0, '.')
import warnings
warnings.filterwarnings('ignore')
import ezdxf
from shapely.geometry import Polygon, box
from shapely.affinity import scale
from shapely.ops import unary_union

print("=" * 60)
print("ESTATE PLANNER DEBUG")
print("=" * 60)

# Load DXF
dxf_path = r"D:\Gitrepo\REMB\examples\Lot Plan Bel air Technical Description.dxf"
doc = ezdxf.readfile(dxf_path)
msp = doc.modelspace()

# Extract boundary
print("\n1. EXTRACTING BOUNDARY")
for entity in msp.query('LWPOLYLINE'):
    coords = [(p[0], p[1]) for p in entity.get_points('xy')]
    if len(coords) >= 3:
        poly = Polygon(coords)
        if poly.is_valid and poly.area > 1000:
            print("   Found: layer='%s', area=%.0f mm2" % (entity.dxf.layer, poly.area))
            
            # Convert mm to m (divide by 1000)
            boundary_m = scale(poly, xfact=0.001, yfact=0.001, origin=(0,0))
            print("   Converted: %.2f m2" % boundary_m.area)
            print("   Bounds: (%.2f, %.2f) to (%.2f, %.2f)" % boundary_m.bounds)
            
            # Apply setback
            print("\n2. APPLYING SETBACK (1m)")
            setback = boundary_m.buffer(-1.0)  # Buffer inward by 1m
            print("   Setback area: %.2f m2" % setback.area)
            
            if setback.is_empty:
                print("   WARNING: Setback too large, trying 0.5m")
                setback = boundary_m.buffer(-0.5)
                print("   Setback area: %.2f m2" % setback.area)
            
            # Skip road for small parcel - just use setback as usable
            print("\n3. USABLE AREA (no road for small parcel)")
            usable = setback
            print("   Usable area: %.2f m2" % usable.area)
            
            # Generate plots
            print("\n4. GENERATING PLOTS")
            minx, miny, maxx, maxy = usable.bounds
            print("   Bounds: x=[%.2f, %.2f], y=[%.2f, %.2f]" % (minx, maxx, miny, maxy))
            
            plot_w = 4.0  # 4m wide
            plot_h = 5.0  # 5m tall
            spacing = 0.5  # 0.5m between plots
            
            plots = []
            x = minx + spacing
            while x + plot_w < maxx - spacing:
                y = miny + spacing
                while y + plot_h < maxy - spacing:
                    candidate = box(x, y, x + plot_w, y + plot_h)
                    
                    # Check if COMPLETELY inside usable area
                    if usable.contains(candidate):
                        # Check no overlaps
                        overlap = False
                        for existing in plots:
                            if candidate.intersects(existing):
                                overlap = True
                                break
                        
                        if not overlap:
                            plots.append(candidate)
                            print("     Plot %d: (%.1f, %.1f)" % (len(plots), x, y))
                    
                    y += plot_h + spacing
                x += plot_w + spacing
            
            print("\n   TOTAL PLOTS: %d" % len(plots))
            
            if len(plots) == 0:
                print("\n   DEBUG: Testing single plot at center...")
                cx = (minx + maxx) / 2 - plot_w / 2
                cy = (miny + maxy) / 2 - plot_h / 2
                test_plot = box(cx, cy, cx + plot_w, cy + plot_h)
                print("     Center: (%.2f, %.2f)" % (cx, cy))
                print("     Contains? %s" % usable.contains(test_plot))
                print("     Intersects? %s" % usable.intersects(test_plot))
                
            # Now export with plots
            if plots:
                print("\n5. EXPORTING DXF")
                
                # Create layers
                if 'PLOTS_NEW' not in doc.layers:
                    doc.layers.add('PLOTS_NEW', color=5)
                
                # Draw plots  
                scale_back = 1000  # m to mm
                for i, plot_geom in enumerate(plots):
                    px, py, px2, py2 = plot_geom.bounds
                    points = [
                        (px * scale_back, py * scale_back),
                        (px2 * scale_back, py * scale_back),
                        (px2 * scale_back, py2 * scale_back),
                        (px * scale_back, py2 * scale_back)
                    ]
                    msp.add_lwpolyline(points, close=True, dxfattribs={'layer': 'PLOTS_NEW', 'color': 5})
                    
                    # Label
                    cx = (px + px2) / 2 * scale_back
                    cy = (py + py2) / 2 * scale_back
                    msp.add_mtext(
                        "PLOT_%03d\n%.0fx%.0fm" % (i+1, plot_w, plot_h),
                        dxfattribs={'layer': 'PLOTS_NEW', 'char_height': 200}
                    ).set_location((cx, cy))
                
                output_path = r"D:\Gitrepo\REMB\output\Bel_Air_DEBUG.dxf"
                doc.saveas(output_path)
                print("   Saved: %s" % output_path)
                
                import os
                print("   Size: %.1f KB" % (os.path.getsize(output_path)/1024))
                
            break  # Only process first valid polygon
