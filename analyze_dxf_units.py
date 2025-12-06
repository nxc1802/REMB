# Quick analysis of the DXF file
import sys
sys.path.insert(0, '.')
import ezdxf

dxf_path = r"D:\Gitrepo\REMB\examples\Lot Plan Bel air Technical Description.dxf"
doc = ezdxf.readfile(dxf_path)
msp = doc.modelspace()

print("=" * 60)
print("DXF FILE ANALYSIS")
print("=" * 60)

# Check units
unit_code = doc.header.get('$INSUNITS', 0)
units = {0: 'Unitless', 1: 'Inches', 2: 'Feet', 3: 'Miles',
         4: 'Millimeters', 5: 'Centimeters', 6: 'Meters', 7: 'Kilometers'}
print("\nUnit system: %s (code %d)" % (units.get(unit_code, 'Unknown'), unit_code))

# Get all layers
print("\nLayers:")
for layer in doc.layers:
    print("  - %s" % layer.dxf.name)

# Get polylines
print("\nPolylines (sorted by area):")
polylines = []
for entity in msp.query('LWPOLYLINE'):
    coords = [(p[0], p[1]) for p in entity.get_points('xy')]
    if len(coords) >= 3:
        from shapely.geometry import Polygon
        try:
            poly = Polygon(coords)
            if poly.is_valid:
                polylines.append({
                    'layer': entity.dxf.layer,
                    'area': poly.area,
                    'bounds': poly.bounds,
                    'is_closed': entity.is_closed
                })
        except:
            pass

polylines.sort(key=lambda x: x['area'], reverse=True)
for i, p in enumerate(polylines[:5]):
    bnd = p['bounds']
    width = bnd[2] - bnd[0]
    height = bnd[3] - bnd[1]
    print("  %d. Layer '%s': area=%.0f, size=%.0f x %.0f, closed=%s" % (
        i+1, p['layer'], p['area'], width, height, p['is_closed']
    ))

# Check if units might be millimeters
if polylines:
    largest = polylines[0]
    bnd = largest['bounds']
    width = bnd[2] - bnd[0]
    height = bnd[3] - bnd[1]
    
    print("\n" + "=" * 60)
    print("SCALE ANALYSIS")
    print("=" * 60)
    print("\nLargest polyline:")
    print("  Width: %.2f" % width)
    print("  Height: %.2f" % height)
    print("  Area: %.0f" % largest['area'])
    
    # Check if this looks like millimeters
    if width > 10000 or height > 10000 or largest['area'] > 1000000:
        print("\n*** LIKELY IN MILLIMETERS ***")
        print("  Width in meters: %.2f m" % (width / 1000))
        print("  Height in meters: %.2f m" % (height / 1000))
        print("  Area in m2: %.2f m2" % (largest['area'] / 1000000))
    elif width > 100 or height > 100 or largest['area'] > 10000:
        print("\n*** LIKELY IN METERS ***")
        print("  Already in meters: %.2f x %.2f m" % (width, height))
        print("  Area: %.2f m2" % largest['area'])
    else:
        print("\n*** LIKELY IN CENTIMETERS ***")
        print("  Width in meters: %.2f m" % (width / 100))
        print("  Height in meters: %.2f m" % (height / 100))
