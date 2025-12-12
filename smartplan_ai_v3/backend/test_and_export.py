"""Test script to generate assets and export to GeoJSON."""
import httpx
import json
import time

API_URL = "http://localhost:8003"
DXF_PATH = "/Volumes/WorkSpace/Project/REMB/examples/663409.dxf"
OUTPUT_PATH = "output_plan.geojson"

def main():
    print("=" * 60)
    print("SmartPlan AI v3.0 - End-to-End Test")
    print("=" * 60)
    
    # 1. Upload DXF
    print("\n📂 Step 1: Uploading DXF file...")
    with open(DXF_PATH, 'rb') as f:
        files = {'file': f}
        r = httpx.post(f"{API_URL}/api/upload-dxf", files=files, params={"road_width": 12}, timeout=30.0)
    
    if r.status_code != 200:
        print(f"❌ Upload failed: {r.text}")
        return
    
    state = r.json()
    print(f"✅ Boundary: {state['total_area']:.0f}m² ({state['total_area']/10000:.2f}ha)")
    print(f"✅ Blocks: {len(state['blocks'])}")
    
    block_id = state['blocks'][0]['id']
    
    # 2. Generate assets with various commands
    commands = [
        "Tạo đường hình chữ thập",
        "Thêm 3 nhà máy",
        "Thêm 2 bãi đỗ xe",
        "Thêm 1 khu cây xanh",
    ]
    
    for i, cmd in enumerate(commands, 1):
        print(f"\n💬 Step {i+1}: '{cmd}'...")
        
        # Generate
        payload = {"block_id": block_id, "user_request": cmd}
        r = httpx.post(f"{API_URL}/api/blocks/{block_id}/generate", json=payload, timeout=60.0)
        if r.status_code != 200:
            print(f"  ❌ Generate failed: {r.text}")
            continue
        
        gen_result = r.json()
        if not gen_result['success']:
            print(f"  ❌ Error: {gen_result.get('error')}")
            continue
        
        action = gen_result.get('action', 'add')
        print(f"  📦 Action: {action}, Assets: {len(gen_result['new_assets'])}")
        
        # Handle clear action
        if action == 'clear':
            r = httpx.delete(f"{API_URL}/api/blocks/{block_id}/assets", timeout=10.0)
            print(f"  🗑️ Cleared assets")
            continue
        
        # Validate
        val_payload = {"block_id": block_id, "new_assets": gen_result['new_assets']}
        r = httpx.post(f"{API_URL}/api/validate", json=val_payload, timeout=30.0)
        if r.status_code != 200:
            print(f"  ❌ Validate failed: {r.text}")
            continue
        
        val_result = r.json()
        if val_result['success']:
            print(f"  ✅ Added {len(gen_result['new_assets'])} assets")
        else:
            print(f"  ⚠️ Errors: {val_result['errors']}")
        
        time.sleep(1)  # Rate limit
    
    # 3. Get final state
    print("\n📊 Step 6: Getting final state...")
    r = httpx.get(f"{API_URL}/api/state", timeout=10.0)
    state = r.json()
    
    # 4. Export to GeoJSON
    print(f"\n📁 Step 7: Exporting to {OUTPUT_PATH}...")
    
    features = []
    
    # Add boundary
    if state['boundary']:
        features.append({
            "type": "Feature",
            "properties": {"role": "boundary", "area": state['total_area']},
            "geometry": {
                "type": "Polygon",
                "coordinates": [state['boundary']]
            }
        })
    
    # Add blocks and assets
    for block in state['blocks']:
        features.append({
            "type": "Feature",
            "properties": {"role": "block", "id": block['id'], "area": block['area']},
            "geometry": {
                "type": "Polygon", 
                "coordinates": [block['polygon']]
            }
        })
        
        for j, asset in enumerate(block['assets']):
            features.append({
                "type": "Feature",
                "properties": {
                    "role": "asset",
                    "type": asset['type'],
                    "block_id": block['id'],
                    "asset_index": j
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [asset['polygon']]
                }
            })
    
    geojson = {
        "type": "FeatureCollection",
        "name": "SmartPlan_AI_v3_Output",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}},
        "features": features
    }
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, indent=2, ensure_ascii=False)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"Total Area: {state['total_area']:.0f}m² ({state['total_area']/10000:.2f}ha)")
    print(f"Blocks: {len(state['blocks'])}")
    
    total_assets = 0
    asset_counts = {}
    for block in state['blocks']:
        for asset in block['assets']:
            total_assets += 1
            t = asset['type']
            asset_counts[t] = asset_counts.get(t, 0) + 1
    
    print(f"Total Assets: {total_assets}")
    for atype, count in asset_counts.items():
        print(f"  - {atype}: {count}")
    
    print(f"\n✅ Exported to: {OUTPUT_PATH}")
    print(f"   Features: {len(features)}")

if __name__ == "__main__":
    main()
