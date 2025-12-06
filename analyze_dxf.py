"""Analyze DXF file contents"""
import ezdxf

doc = ezdxf.readfile('output/full_flow_test_layout.dxf')
msp = doc.modelspace()

print('=== DXF PLOT DETAILS ===')
print()

# Analyze polylines (plots and boundaries)
polylines = [e for e in msp if e.dxftype() == 'LWPOLYLINE']
print(f'Polylines found: {len(polylines)}')
print()

plot_count = 0
for i, poly in enumerate(polylines):
    points = list(poly.get_points())
    if len(points) >= 4:
        # Calculate bounds
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        width = max_x - min_x
        height = max_y - min_y
        area = width * height
        
        if area > 100000:
            print(f'[SITE BOUNDARY]')
            print(f'  Bounds: ({min_x:.0f}, {min_y:.0f}) to ({max_x:.0f}, {max_y:.0f})')
            print(f'  Size: {width:.0f}m x {height:.0f}m = {area:,.0f} m²')
            print()
        elif area > 100:
            plot_count += 1
            print(f'[PLOT {plot_count}]')
            print(f'  Position: ({min_x:.0f}, {min_y:.0f})')
            print(f'  Size: {width:.1f}m x {height:.1f}m')
            print(f'  Area: {area:,.0f} m²')
            print()

# Analyze text labels
texts = [e for e in msp if e.dxftype() == 'TEXT']
print(f'Text labels: {len(texts)}')
sample_texts = [text.dxf.text for text in texts[:15]]
for t in sample_texts:
    print(f'  - "{t}"')

print()
print('=== SUMMARY ===')
print(f'Total plots: {plot_count}')
print(f'Total polylines: {len(polylines)}')
print(f'Total text labels: {len(texts)}')
