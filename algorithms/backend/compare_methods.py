"""Compare file read vs stream read"""

import ezdxf

dxf_path = "/Volumes/WorkSpace/Project/REMB/examples/663409.dxf"

# Method 1: Direct readfile
print("Method 1: Direct readfile()")
doc1 = ezdxf.readfile(dxf_path)
msp1 = doc1.modelspace()
lines1 = len(list(msp1.query('LINE')))
print(f"  LINE entities: {lines1}")

# Method 2: Read bytes, decode, StringIO
import io
with open(dxf_path, 'rb') as f:
    content = f.read()

print("\nMethod 2: bytes -> latin-1 -> StringIO")
text = content.decode('latin-1')
stream = io.StringIO(text)
doc2 = ezdxf.read(stream)
msp2 = doc2.modelspace()
lines2 = len(list(msp2.query('LINE')))
print(f"  LINE entities: {lines2}")

# Method 3: tempfile
import tempfile
import os

print("\nMethod 3: bytes -> tempfile -> readfile()")
with tempfile.NamedTemporaryFile(mode='wb', suffix='.dxf', delete=False) as tmp:
    tmp.write(content)
    tmp_path = tmp.name

doc3 = ezdxf.readfile(tmp_path)
msp3 = doc3.modelspace()
lines3 = len(list(msp3.query('LINE')))
print(f"  LINE entities: {lines3}")
os.unlink(tmp_path)
