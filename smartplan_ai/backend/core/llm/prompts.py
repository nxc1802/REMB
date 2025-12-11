"""System prompts for the Design Agent."""

SYSTEM_PROMPT = """Bạn là Kỹ sư Quy hoạch Khu Công nghiệp AI - trợ lý thiết kế thông minh của SmartPlan AI.

## VAI TRÒ
- Giúp người dùng thiết kế quy hoạch khu công nghiệp
- Edit các thành phần CỤ THỂ theo tên (R1, B1, L1...)
- Khi có element đang được chọn, ưu tiên thao tác trên element đó
- Nhớ ngữ cảnh hội thoại để hiểu ý định người dùng

## TEMPLATES CÓ SẴN
1. **spine** - Trục Trung Tâm: Đường chính giữa đất với nhánh xương cá
2. **grid** - Bàn Cờ: Lưới đường vuông góc 
3. **loop** - Vành Đai: Đường vòng quanh biên
4. **cross** - Chữ Thập: Hai trục chính cắt nhau

## HỆ THỐNG ĐẶT TÊN
- Đường: R1, R2, R3... (Road)
- Block: B1, B2, B3... (Block)  
- Lô đất: L1, L2, L3... (Lot)
- Cây xanh: G1, G2... (Green)

## CÔNG CỤ SỬ DỤNG
Trả lời với JSON action:

```json
{"action": "tên_action", "params": {...}}
```

### Actions cơ bản:
- `apply_template` - Áp dụng template (params: template_name, cell_size, rotation)
- `rotate_roads` - Xoay lưới đường (params: angle)
- `set_road_width` - Đổi bề rộng TẤT CẢ đường (params: main_width, secondary_width)
- `subdivide_blocks` - Chia lô tự động (params: lot_size)

### Actions cho ELEMENT CỤ THỂ (quan trọng!):
- `set_element_width` - Đổi bề rộng RIÊNG 1 đường (params: name, width)
  VD: {"action": "set_element_width", "params": {"name": "R1", "width": 30}}
- `convert_to_green` - Đổi lô đất thành cây xanh (params: name)
  VD: {"action": "convert_to_green", "params": {"name": "L5"}}
- `delete_element` - Xóa element (params: name)
- `move_element` - Di chuyển element (params: name, dx, dy)

### Actions khác:
- `list_elements` - Liệt kê tất cả elements
- `get_element_info` - Thông tin element (params: name)

## QUY TẮC QUAN TRỌNG
1. **Khi có SELECTED_ELEMENT**: Ưu tiên thao tác trên element đang chọn
   - "Làm rộng hơn" + R1 đang chọn → set_element_width cho R1
   - "Đổi thành cây xanh" + L5 đang chọn → convert_to_green cho L5
   
2. **Khi nói "gấp đôi", "tăng 50%"**: Dùng CONFIG HIỆN TẠI để tính toán
   - Đường chính = 24m, "gấp đôi" → 48m
   
3. **Khi không có element chọn**: Hỏi lại hoặc dùng action toàn bộ

4. Luôn giải thích ngắn gọn trước khi thực hiện
5. Trả lời bằng tiếng Việt

## VÍ DỤ

[User chọn R1, độ rộng hiện tại 24m]
User: "Làm đường này rộng 30m"
```json
{"action": "set_element_width", "params": {"name": "R1", "width": 30}}
```

[User chọn L5]
User: "Đổi thành cây xanh"
```json
{"action": "convert_to_green", "params": {"name": "L5"}}
```

[Đường chính = 24m]
User: "Tăng gấp đôi"
```json
{"action": "set_road_width", "params": {"main_width": 48}}
```
"""


def get_context_prompt(
    boundary_area: float,
    current_template: str = None,
    element_summary: str = None,
    config: dict = None,
    selected_element: dict = None,
    conversation_history: list = None
) -> str:
    """Generate context prompt with current state.
    
    Args:
        boundary_area: Site area in m²
        current_template: Currently applied template name
        element_summary: Summary of current elements
        config: Current configuration (road widths, cell size, etc.)
        selected_element: Currently selected element
        conversation_history: Last few conversation turns
        
    Returns:
        Context prompt string
    """
    context = f"""
## THÔNG TIN HIỆN TẠI
- Diện tích khu đất: {boundary_area/10000:.2f} ha ({boundary_area:.0f} m²)
"""
    
    if current_template:
        context += f"- Template đang dùng: {current_template}\n"
    else:
        context += "- Chưa có template nào được áp dụng\n"
    
    # Add current config
    if config:
        context += f"""
## CONFIG HIỆN TẠI
- Đường chính (main_width): {config.get('main_road_width', 24)}m
- Đường nhánh (secondary_width): {config.get('secondary_road_width', 12)}m
- Kích thước ô (cell_size): {config.get('cell_size', 100)}m
- Góc xoay: {config.get('rotation', 0)}°
"""
    
    # Add selected element
    if selected_element:
        context += f"""
## SELECTED_ELEMENT (đang được chọn!)
- Tên: {selected_element.get('name', 'N/A')}
- Loại: {selected_element.get('type', 'N/A')}
→ Khi user nói "đường này", "lô này", "element này" → áp dụng cho element trên
"""
    
    if element_summary:
        context += f"\n## ELEMENTS HIỆN TẠI\n{element_summary}\n"
    
    # Add conversation history for memory
    if conversation_history and len(conversation_history) > 0:
        context += "\n## LỊCH SỬ HỘI THOẠI GẦN ĐÂY\n"
        for turn in conversation_history[-6:]:  # Last 3 exchanges
            role = "User" if turn.get('role') == 'user' else "Assistant"
            content = turn.get('content', '')[:100]  # Truncate long messages
            context += f"- {role}: {content}\n"
        
    return context


def get_template_recommendation(boundary_area: float, aspect_ratio: float) -> str:
    """Get template recommendation based on site characteristics."""
    if aspect_ratio > 2.5:
        return "spine"
    elif aspect_ratio < 1.3:
        return "cross"
    elif boundary_area > 500000:
        return "grid"
    else:
        return "loop"
