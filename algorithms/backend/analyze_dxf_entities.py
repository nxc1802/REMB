"""Investigate what entities are in these DXF files."""

import ezdxf
import tempfile
import os

files = [
    "/Volumes/WorkSpace/Project/REMB/examples/663409.dxf",
    "/Volumes/WorkSpace/Project/REMB/examples/930300.dxf"
]

for dxf_path in files:
    print("=" * 70)
    print(f"Analyzing: {dxf_path.split('/')[-1]}")
    print("=" * 70)
    
    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
        
        # Count all entity types
        entity_types = {}
        total = 0
        
        for entity in msp:
            etype = entity.dxftype()
            entity_types[etype] = entity_types.get(etype, 0) + 1
            total += 1
        
        print(f"Total entities: {total}")
        print(f"\nEntity breakdown:")
        for etype, count in sorted(entity_types.items(), key=lambda x: -x[1]):
            print(f"  {etype}: {count}")
        
        # Check for specific geometry types
        print(f"\nGeometry analysis:")
        
        # Check for POINT entities
        points = list(msp.query('POINT'))
        if points:
            print(f"  Found {len(points)} POINT entities")
            print(f"    Sample: {points[0].dxf.location if points else 'N/A'}")
        
        # Check for CIRCLE entities
        circles = list(msp.query('CIRCLE'))
        if circles:
            print(f"  Found {len(circles)} CIRCLE entities")
            if circles:
                c = circles[0]
                print(f"    Sample: center={c.dxf.center}, radius={c.dxf.radius}")
        
        # Check for ARC entities
        arcs = list(msp.query('ARC'))
        if arcs:
            print(f"  Found {len(arcs)} ARC entities")
        
        # Check for SPLINE entities
        splines = list(msp.query('SPLINE'))
        if splines:
            print(f"  Found {len(splines)} SPLINE entities")
        
        # Check for TEXT entities
        texts = list(msp.query('TEXT'))
        if texts:
            print(f"  Found {len(texts)} TEXT entities")
            if texts:
                print(f"    Sample text: '{texts[0].dxf.text}'")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
