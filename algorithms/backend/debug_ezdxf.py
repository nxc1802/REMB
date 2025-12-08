"""Debug ezdxf behavior with Bel air file"""
import ezdxf
import io

dxf_path = "/Volumes/WorkSpace/Project/REMB/examples/Lot Plan Bel air Technical Description.dxf"

# Test 1: Direct file read
print("Test 1: Direct file read")
try:
    doc = ezdxf.readfile(dxf_path)
    print(f"✅ Success with readfile()")
    print(f"   Entities: {len(list(doc.modelspace()))}")
except Exception as e:
    print(f"❌ Failed: {e}")

# Test 2: Read through bytes
print("\nTest 2: Read through bytes")
with open(dxf_path, 'rb') as f:
    content = f.read()

# Try decoding
for enc in ['utf-8', 'latin-1', 'cp1252']:
    print(f"\n  Trying {enc}:")
    try:
        text = content.decode(enc)
        stream = io.StringIO(text)
        doc = ezdxf.read(stream)
        print(f"  ✅ Success with {enc}")
        break
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {str(e)[:100]}")

# Test 3: Binary stream
print("\nTest 3: Binary stream")
try:
    stream = io.BytesIO(content)
    doc = ezdxf.read(stream)
    print(f"✅ Success with binary stream")
except Exception as e:
    print(f"❌ Failed: {e}")
