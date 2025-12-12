"""Comprehensive API test script for SmartPlan AI v3.0"""
import httpx
import json
import time
import sys

API_URL = "http://localhost:8003"
DXF_PATH = "/Volumes/WorkSpace/Project/REMB/examples/663409.dxf"

def test_endpoint(name: str, success: bool, result: str):
    """Print test result."""
    status = "✅" if success else "❌"
    print(f"{status} {name}: {result}")
    return success

def main():
    print("=" * 70)
    print("SmartPlan AI v3.0 - Comprehensive API Test")
    print("=" * 70)
    
    results = []
    
    # 1. Health Check
    print("\n📌 1. HEALTH & STATUS")
    try:
        r = httpx.get(f"{API_URL}/health", timeout=5.0)
        results.append(test_endpoint("GET /health", r.status_code == 200, r.json().get("status", "unknown")))
    except Exception as e:
        results.append(test_endpoint("GET /health", False, str(e)))
    
    # 2. Reset state
    print("\n📌 2. RESET STATE")
    try:
        r = httpx.delete(f"{API_URL}/api/reset", timeout=5.0)
        results.append(test_endpoint("DELETE /api/reset", r.status_code == 200, r.json().get("status", "failed")))
    except Exception as e:
        results.append(test_endpoint("DELETE /api/reset", False, str(e)))
    
    # 3. Model Management
    print("\n📌 3. MODEL MANAGEMENT")
    try:
        r = httpx.get(f"{API_URL}/api/models", timeout=5.0)
        data = r.json()
        results.append(test_endpoint("GET /api/models", r.status_code == 200, 
            f"Current: {data.get('current_provider')}/{data.get('current_model')}"))
    except Exception as e:
        results.append(test_endpoint("GET /api/models", False, str(e)))
    
    try:
        r = httpx.post(f"{API_URL}/api/models/switch?provider=megallm&model=llama3.3-70b-instruct", timeout=5.0)
        results.append(test_endpoint("POST /api/models/switch", r.status_code == 200, "Switched to megallm"))
    except Exception as e:
        results.append(test_endpoint("POST /api/models/switch", False, str(e)))
    
    # 4. DXF Upload
    print("\n📌 4. DXF UPLOAD")
    try:
        with open(DXF_PATH, 'rb') as f:
            r = httpx.post(f"{API_URL}/api/upload-dxf", files={'file': f}, params={"road_width": 12}, timeout=30.0)
        data = r.json()
        results.append(test_endpoint("POST /api/upload-dxf", r.status_code == 200, 
            f"Area: {data.get('total_area', 0):.0f}m², Blocks: {len(data.get('blocks', []))}"))
    except Exception as e:
        results.append(test_endpoint("POST /api/upload-dxf", False, str(e)))
    
    # 5. Boundary & Blocks
    print("\n📌 5. BOUNDARY & BLOCKS")
    sample_boundary = [[0, 0], [200, 0], [200, 150], [0, 150], [0, 0]]
    try:
        r = httpx.post(f"{API_URL}/api/set-boundary", json={"boundary": sample_boundary, "road_width": 12}, timeout=10.0)
        results.append(test_endpoint("POST /api/set-boundary", r.status_code == 200, 
            f"Blocks: {len(r.json().get('blocks', []))}"))
    except Exception as e:
        results.append(test_endpoint("POST /api/set-boundary", False, str(e)))
    
    try:
        r = httpx.get(f"{API_URL}/api/blocks", timeout=5.0)
        blocks = r.json()
        results.append(test_endpoint("GET /api/blocks", r.status_code == 200, f"Found {len(blocks)} blocks"))
        block_id = blocks[0]["id"] if blocks else "B1"
    except Exception as e:
        results.append(test_endpoint("GET /api/blocks", False, str(e)))
        block_id = "B1"
    
    try:
        r = httpx.get(f"{API_URL}/api/blocks/{block_id}", timeout=5.0)
        results.append(test_endpoint(f"GET /api/blocks/{block_id}", r.status_code == 200, 
            f"Area: {r.json().get('area', 0):.0f}m²"))
    except Exception as e:
        results.append(test_endpoint(f"GET /api/blocks/{block_id}", False, str(e)))
    
    # 6. State Management
    print("\n📌 6. STATE MANAGEMENT")
    try:
        r = httpx.get(f"{API_URL}/api/state", timeout=5.0)
        data = r.json()
        results.append(test_endpoint("GET /api/state", r.status_code == 200, 
            f"Coverage: {data.get('coverage_ratio', 0)*100:.1f}%"))
    except Exception as e:
        results.append(test_endpoint("GET /api/state", False, str(e)))
    
    # 7. Asset Generation (LLM)
    print("\n📌 7. ASSET GENERATION (LLM)")
    try:
        payload = {"block_id": block_id, "user_request": "Thêm 1 nhà kho"}
        r = httpx.post(f"{API_URL}/api/blocks/{block_id}/generate", json=payload, timeout=60.0)
        data = r.json()
        if data.get("success"):
            results.append(test_endpoint("POST /api/blocks/.../generate", True, 
                f"Generated {len(data.get('new_assets', []))} assets"))
        else:
            results.append(test_endpoint("POST /api/blocks/.../generate", False, data.get("error", "Unknown")))
    except Exception as e:
        results.append(test_endpoint("POST /api/blocks/.../generate", False, str(e)))
    
    # 8. Validation
    print("\n📌 8. VALIDATION")
    try:
        test_asset = {"type": "warehouse_cold", "polygon": [[10, 10], [50, 10], [50, 40], [10, 40], [10, 10]]}
        payload = {"block_id": block_id, "new_assets": [test_asset]}
        r = httpx.post(f"{API_URL}/api/validate", json=payload, timeout=10.0)
        data = r.json()
        results.append(test_endpoint("POST /api/validate", r.status_code == 200, 
            f"Success: {data.get('success')}, Warnings: {len(data.get('warnings', []))}"))
    except Exception as e:
        results.append(test_endpoint("POST /api/validate", False, str(e)))
    
    # 9. Delete Assets
    print("\n📌 9. DELETE ASSETS")
    try:
        r = httpx.delete(f"{API_URL}/api/blocks/{block_id}/assets", timeout=5.0)
        results.append(test_endpoint("DELETE /api/blocks/.../assets", r.status_code == 200, 
            f"Cleared {r.json().get('cleared_count', 0)} assets"))
    except Exception as e:
        results.append(test_endpoint("DELETE /api/blocks/.../assets", False, str(e)))
    
    # 10. Export
    print("\n📌 10. EXPORT")
    try:
        r = httpx.get(f"{API_URL}/api/export/json", timeout=5.0)
        data = r.json()
        results.append(test_endpoint("GET /api/export/json", r.status_code == 200, 
            f"Blocks: {len(data.get('blocks', []))}"))
    except Exception as e:
        results.append(test_endpoint("GET /api/export/json", False, str(e)))
    
    try:
        r = httpx.get(f"{API_URL}/api/export/geojson", timeout=5.0)
        data = r.json()
        results.append(test_endpoint("GET /api/export/geojson", r.status_code == 200, 
            f"Features: {len(data.get('features', []))}"))
    except Exception as e:
        results.append(test_endpoint("GET /api/export/geojson", False, str(e)))
    
    # 11. Infrastructure (requires assets)
    print("\n📌 11. INFRASTRUCTURE")
    # First add an asset
    try:
        test_asset = {"type": "factory_standard", "polygon": [[20, 20], [80, 20], [80, 60], [20, 60], [20, 20]]}
        r = httpx.post(f"{API_URL}/api/validate", json={"block_id": block_id, "new_assets": [test_asset]}, timeout=10.0)
        
        r = httpx.post(f"{API_URL}/api/finalize", json={"connection_point": [0, 75], "use_steiner": False}, timeout=10.0)
        data = r.json()
        results.append(test_endpoint("POST /api/finalize", r.status_code == 200, 
            f"Electric: {data.get('total_electric_length', 0):.1f}m"))
    except Exception as e:
        results.append(test_endpoint("POST /api/finalize", False, str(e)))
    
    # Summary
    print("\n" + "=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"📊 SUMMARY: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print("=" * 70)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
