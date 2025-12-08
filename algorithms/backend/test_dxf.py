"""Test DXF loading functionality."""

import sys
sys.path.insert(0, '/Volumes/WorkSpace/Project/REMB/algorithms/backend')

from utils.dxf_utils import load_boundary_from_dxf, validate_dxf

# Test with actual DXF file
dxf_path = "/Volumes/WorkSpace/Project/REMB/examples/api-cw750-details.dxf"

with open(dxf_path, 'rb') as f:
    content = f.read()
    
print(f"File size: {len(content)} bytes")
print(f"First 100 bytes: {content[:100]}")

# Test validation
is_valid, message = validate_dxf(content)
print(f"\nValidation: {is_valid}")
print(f"Message: {message}")

# Test loading
if is_valid:
    polygon = load_boundary_from_dxf(content)
    if polygon:
        print(f"\n✅ Success!")
        print(f"Polygon area: {polygon.area/10000:.2f} ha")
        print(f"Bounds: {polygon.bounds}")
    else:
        print("\n❌ Failed to extract polygon")
