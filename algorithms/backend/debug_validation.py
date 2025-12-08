"""Debug validation process for 663409.dxf"""

import sys
sys.path.insert(0, '/Volumes/WorkSpace/Project/REMB/algorithms/backend')

import ezdxf
import io
import tempfile
import os

dxf_path = "/Volumes/WorkSpace/Project/REMB/examples/663409.dxf"

with open(dxf_path, 'rb') as f:
    dxf_content = f.read()

print(f"File size: {len(dxf_content)} bytes")

# Try to load with different methods
encodings = ['utf-8', 'latin-1', 'cp1252', 'utf-16']
doc = None

for encoding in encodings:
    print(f"\nTrying {encoding}...")
    try:
        text_content = dxf_content.decode(encoding)
        text_stream = io.StringIO(text_content)
        doc = ezdxf.read(text_stream)
        print(f"  ✅ Success with {encoding}")
        break
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {str(e)[:80]}")

if doc is None:
    print("\nTrying binary stream...")
    try:
        dxf_stream = io.BytesIO(dxf_content)
        doc = ezdxf.read(dxf_stream)
        print("  ✅ Success with binary stream")
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {str(e)[:80]}")

if doc is None:
    print("\nTrying tempfile...")
    try:
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.dxf', delete=False) as tmp:
            tmp.write(dxf_content)
            tmp_path = tmp.name
        
        doc = ezdxf.readfile(tmp_path)
        print(f"  ✅ Success with tempfile")
        os.unlink(tmp_path)
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {str(e)[:80]}")
        try:
            os.unlink(tmp_path)
        except:
            pass

if doc:
    msp = doc.modelspace()
    lwpolylines = sum(1 for e in msp if e.dxftype() == 'LWPOLYLINE')
    polylines = len(list(msp.query('POLYLINE')))
    lines = len(list(msp.query('LINE')))
    
    print(f"\n✅ LOADED SUCCESSFULLY")
    print(f"   LWPOLYLINE: {lwpolylines}")
    print(f"   POLYLINE: {polylines}")
    print(f"   LINE: {lines}")
    print(f"   Total: {lwpolylines + polylines + lines}")
else:
    print("\n❌ FAILED TO LOAD")
