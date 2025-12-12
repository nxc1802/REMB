"""System prompts for Gemini 2.5 Flash Spatial Planner.

Based on LLM_Full.md Section 4 - System Prompt specification.
"""

from typing import List, Dict, Any


# Asset keywords that AI is allowed to use
ASSET_KEYWORDS = [
    "factory_standard",
    "warehouse_cold", 
    "office_hq",
    "parking_lot",
    "green_buffer",
    "utility_station",
    "internal_road"
]


SYSTEM_PROMPT = """BẠN LÀ MỘT AI SPATIAL PLANNER. BẠN CHỈ TRẢ VỀ JSON THUẦN TÚY.
Output format:
```json
{
  "action": "add",
  "new_assets": [
    {"type": "internal_road", "polygon": [[100, 200], [150, 200], [150, 210], [100, 210], [100, 200]]}
  ],
  "explanation": "Giải thích ngắn"
}
```

ACTION TYPES:
- "add": Thêm assets mới (mặc định)
- "clear": Xóa TẤT CẢ assets hiện có (new_assets = [])
- "replace": Xóa assets cũ và thay bằng assets mới

RULES:
1. new_assets PHẢI nằm trong boundary
2. Polygon: 4+ điểm, khép kín
3. type: factory_standard, warehouse_cold, office_hq, parking_lot, green_buffer, utility_station, internal_road

MAPPING:
nhà máy → factory_standard | kho → warehouse_cold | văn phòng → office_hq
bãi xe → parking_lot | cây xanh → green_buffer | trạm kỹ thuật → utility_station
đường → internal_road
xóa/xoá/delete/clear → action: "clear"
"""


def build_context_prompt(
    boundary_coords: List[List[float]],
    existing_assets: List[Dict[str, Any]],
    user_request: str
) -> str:
    """Build context prompt for LLM with current state.
    
    Args:
        boundary_coords: Boundary polygon coordinates
        existing_assets: List of existing asset dicts
        user_request: User's request in natural language
        
    Returns:
        Formatted context prompt string
    """
    # Calculate boundary extents
    if boundary_coords:
        xs = [c[0] for c in boundary_coords]
        ys = [c[1] for c in boundary_coords]
        bounds_info = f"X: {min(xs):.1f} → {max(xs):.1f}, Y: {min(ys):.1f} → {max(ys):.1f}"
    else:
        bounds_info = "N/A"
    
    # Calculate center point for spatial hints
    center_x = (min(xs) + max(xs)) / 2 if boundary_coords else 0
    center_y = (min(ys) + max(ys)) / 2 if boundary_coords else 0
    width = max(xs) - min(xs) if boundary_coords else 0
    height = max(ys) - min(ys) if boundary_coords else 0
    
    # Format existing assets count
    existing_count = len(existing_assets)
    
    # Build existing assets description
    existing_desc = ""
    if existing_assets:
        existing_desc = "\n### ⚠️ VÙNG CẤM (PHẢI TRÁNH VA CHẠM):\n"
        for i, asset in enumerate(existing_assets):
            asset_type = asset.get("type", "unknown")
            polygon = asset.get("polygon", [])
            if polygon:
                min_x = min(p[0] for p in polygon)
                max_x = max(p[0] for p in polygon)
                min_y = min(p[1] for p in polygon)
                max_y = max(p[1] for p in polygon)
                existing_desc += f"- {asset_type} #{i}: X [{min_x:.0f}→{max_x:.0f}], Y [{min_y:.0f}→{max_y:.0f}]\n"
        existing_desc += "\n**QUAN TRỌNG: Asset mới KHÔNG ĐƯỢC có tọa độ nằm trong các vùng trên!**\n"
    
    # Calculate safe zones (quadrants separated by roads at center)
    safe_zones = f"""
### ✅ VÙNG AN TOÀN ĐỂ ĐẶT ASSETS:
- Góc 1 (trên-trái): X [{min(xs):.0f}→{center_x-10:.0f}], Y [{center_y+10:.0f}→{max(ys):.0f}]
- Góc 2 (trên-phải): X [{center_x+10:.0f}→{max(xs):.0f}], Y [{center_y+10:.0f}→{max(ys):.0f}]
- Góc 3 (dưới-trái): X [{min(xs):.0f}→{center_x-10:.0f}], Y [{min(ys):.0f}→{center_y-10:.0f}]
- Góc 4 (dưới-phải): X [{center_x+10:.0f}→{max(xs):.0f}], Y [{min(ys):.0f}→{center_y-10:.0f}]
"""
    
    # Pre-compute FULL-LENGTH road coordinates (edge to edge)
    road_width = 12
    # Horizontal road: spans full X range, centered on Y
    h_y1 = center_y - road_width/2
    h_y2 = center_y + road_width/2
    h_road = f"[[{min(xs):.0f}, {h_y1:.0f}], [{max(xs):.0f}, {h_y1:.0f}], [{max(xs):.0f}, {h_y2:.0f}], [{min(xs):.0f}, {h_y2:.0f}], [{min(xs):.0f}, {h_y1:.0f}]]"
    
    # Vertical road: spans full Y range, centered on X
    v_x1 = center_x - road_width/2
    v_x2 = center_x + road_width/2
    v_road = f"[[{v_x1:.0f}, {min(ys):.0f}], [{v_x2:.0f}, {min(ys):.0f}], [{v_x2:.0f}, {max(ys):.0f}], [{v_x1:.0f}, {max(ys):.0f}], [{v_x1:.0f}, {min(ys):.0f}]]"
    
    context = f"""
## CONTEXT

Boundary (RANH GIỚI): X [{min(xs):.0f} → {max(xs):.0f}], Y [{min(ys):.0f} → {max(ys):.0f}]
Tâm: ({center_x:.0f}, {center_y:.0f})
Existing Assets: {existing_count}
{existing_desc}{safe_zones}
### User Request: "{user_request}"

### ⚠️ QUAN TRỌNG - QUY TẮC ĐẶT ASSETS:
1. TẤT CẢ tọa độ PHẢI nằm trong Boundary
2. KHÔNG đặt trùng với VÙNG CẤM
3. Nếu tạo đường hình chữ thập, PHẢI dùng CHÍNH XÁC:
   - Đường NGANG: {{"type": "internal_road", "polygon": {h_road}}}
   - Đường DỌC: {{"type": "internal_road", "polygon": {v_road}}}
4. Factory/Warehouse nên có kích thước tối thiểu 50x50m
"""
    return context


def get_generation_config() -> dict:
    """Get Gemini generation configuration.
    
    Returns:
        Generation config dict
    """
    return {
        "temperature": 0.2,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 4096,
    }
