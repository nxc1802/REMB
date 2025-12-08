"""Test additional DXF files."""

import sys
sys.path.insert(0, '/Volumes/WorkSpace/Project/REMB/algorithms/backend')

from utils.dxf_utils import load_boundary_from_dxf, validate_dxf

# Test both files
files = [
    "/Volumes/WorkSpace/Project/REMB/examples/663409.dxf",
    "/Volumes/WorkSpace/Project/REMB/examples/930300.dxf"
]

for dxf_path in files:
    print("=" * 70)
    print(f"Testing: {dxf_path.split('/')[-1]}")
    print("=" * 70)
    
    try:
        with open(dxf_path, 'rb') as f:
            content = f.read()
        
        print(f"File size: {len(content):,} bytes")
        print(f"First 100 bytes: {content[:100]}")
        
        # Test validation
        is_valid, message = validate_dxf(content)
        print(f"\nValidation: {'✅' if is_valid else '❌'} {message}")
        
        # Test loading
        if is_valid:
            polygon = load_boundary_from_dxf(content)
            if polygon:
                print(f"\n✅ Polygon extracted successfully!")
                print(f"   Area: {polygon.area/10000:.2f} ha")
                print(f"   Bounds: {polygon.bounds}")
            else:
                print("\n❌ Failed to extract polygon")
        
    except FileNotFoundError:
        print(f"❌ File not found: {dxf_path}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
