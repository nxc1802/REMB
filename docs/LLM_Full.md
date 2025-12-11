# PROJECT PROPOSAL: SMARTPLAN AI - BACKEND & AI CORE

**Phiên bản:** 3.0 (Backend Focus / Gemini 2.5 Flash / Hybrid Algorithm)
**Mục tiêu:** Xây dựng Core Engine tự động hóa quy hoạch chi tiết với cơ chế kiểm soát chặt chẽ.

-----

## 1\. TỔNG QUAN KIẾN TRÚC (HIGH-LEVEL ARCHITECTURE)

Hệ thống hoạt động như một "Black Box API" nhận dữ liệu thô và trả về kết quả quy hoạch đã được kiểm chứng.

1.  **Geometry Core (Python):** Chịu trách nhiệm cắt đất, quản lý tọa độ, và **Validation (Kiểm tra xung đột)**.
2.  **Generative Engine (Gemini 2.5 Flash):** Chịu trách nhiệm tư duy không gian, bố trí Asset mới dựa trên context hiện có.
3.  **Infrastructure Engine (Graph Algo):** Chịu trách nhiệm đi dây điện/nước tự động vào phút chót (không dùng AI).

-----

## 2\. CẤU TRÚC DỮ LIỆU & TỪ ĐIỂN (DATA STRUCTURE)

Loại bỏ các thông tin hiển thị (màu sắc, 3D model) khỏi ngữ cảnh của AI. AI chỉ cần biết **"Keyword"** để FE sau này tự mapping.

### A. Asset Keyword Mapping (Context cho AI)

Đây là danh sách duy nhất AI được phép sử dụng.

```json
// asset_keywords.json
[
  "factory_standard",
  "warehouse_cold",
  "office_hq",
  "parking_lot",
  "green_buffer",
  "utility_station"
]
```

### B. Cấu trúc Input cho LLM

Khi xử lý một khu đất, AI cần biết: "Đất hình gì?" và "Đang có cái gì ở trỏng rồi?".

```json
{
  "boundary_coords": [[0,0], [100,0], [100,100], [0,100]], // Hình dáng ô đất
  "existing_assets": [
    // Các công trình ĐÃ CÓ (User muốn giữ lại hoặc đã gen từ trước)
    { "type": "office_hq", "polygon": [[10,10], [30,10], [30,30], [10,30]] }
  ],
  "user_request": "Thêm 2 nhà kho lạnh vào phần đất trống còn lại."
}
```

-----

## 3\. LUỒNG XỬ LÝ CHI TIẾT (PROCESSING PIPELINE)

### Giai đoạn 1: Pre-processing (Cắt & Chuẩn bị)

  * **Input:** File DXF (Ranh giới tổng + Đường giao thông).
  * **Action:** Converter chuyển đổi sang GeoJSON. Sử dụng thư viện `Shapely` để thực hiện phép trừ hình học: `Block = Boundary - Road_Network`.
  * **Output:** Danh sách các `Block_ID` và tọa độ Boundary của chúng.

### Giai đoạn 2: Generative Design (LLM Execution)

*Trigger:* Khi User chọn một Block và gửi lệnh.

1.  **Fetch Context:** Backend lấy tọa độ Boundary của Block đó + Danh sách `existing_assets` (nếu có) nằm trong Block.
2.  **Prompting (Gemini 2.5 Flash):**
      * Gửi context JSON và yêu cầu User.
      * Yêu cầu Gemini trả về JSON chứa danh sách `new_assets`.
3.  **LLM Logic:** Gemini tự tính toán khoảng trống còn lại để nhét `new_assets` vào mà không đè lên `existing_assets`.

### Giai đoạn 3: Validation (Conflict Check Function)

Đây là "người gác cổng" (Gatekeeper) quan trọng nhất. Code thuần (Python), không dùng AI.

**Hàm: `validate_and_merge(boundary, existing, new_assets)`**

  * **Rule 1 - Boundary Check:** Tất cả `new_assets` phải nằm trọn vẹn trong `boundary` (dùng `polygon.contains()`).
  * **Rule 2 - Collision Check:**
      * `new_assets` KHÔNG được giao cắt với `existing_assets`.
      * `new_assets` KHÔNG được giao cắt với nhau.
      * (Sử dụng `polygon.intersects()` của Shapely).
  * **Action:**
      * Nếu **Pass**: Trả về danh sách Asset tổng hợp (Cũ + Mới) để lưu DB.
      * Nếu **Fail**: Trả về lỗi cụ thể (ví dụ: "Nhà kho mới bị đè lên văn phòng cũ") và yêu cầu LLM gen lại (hoặc báo lỗi ra API).

### Giai đoạn 4: Infrastructure Routing (Algorithmic Finalization)

*Trigger:* Khi User chốt phương án bố trí công trình (Layout Finalized). **Không dùng LLM.**

1.  **Input:** Danh sách tọa độ tâm (Centroid) của tất cả Assets trong Block + Điểm đấu nối hạ tầng (Cổng/Trạm kỹ thuật).
2.  **Algorithm:** Sử dụng thuật toán đồ thị (Graph Theory).
      * **Điện/Nước:** Dùng **Minimum Spanning Tree (MST)** hoặc **Steiner Tree**.
      * Mục tiêu: Nối tất cả các điểm lại với nhau với tổng chiều dài đường dây ngắn nhất.
      * Ràng buộc: Đường dây nên đi men theo ranh giới các lô đất hoặc đi thẳng ra đường (dùng Grid Graph hoặc Visibility Graph).
3.  **Output:** Danh sách các đường LineString đại diện cho ống nước/dây điện.

-----

## 4\. SYSTEM PROMPT (Dành cho Gemini 2.5 Flash)

```text
ROLE: Bạn là một AI Spatial Planner chuyên nghiệp. Nhiệm vụ của bạn là bổ sung các công trình mới vào một khu đất dựa trên yêu cầu.

MODEL CONFIG:
- Temperature: 0.2 (Ưu tiên tính chính xác, giảm sáng tạo bay bổng)
- Output Format: JSON Only

INPUT CONTEXT:
1. "boundary": Polygon giới hạn khu đất.
2. "existing_assets": Danh sách các Polygon công trình đã tồn tại (Vật cản).
3. "user_request": Yêu cầu thêm mới.
4. "allowed_keywords": [Danh sách từ điển asset]

RULES (TUÂN THỦ TUYỆT ĐỐI):
1. KHÔNG được tạo asset đè lên "existing_assets".
2. KHÔNG được tạo asset nằm ngoài "boundary".
3. Chỉ sử dụng "type" nằm trong "allowed_keywords".
4. Asset mới nên cách asset cũ và boundary một khoảng đệm nhỏ (margin) để đảm bảo an toàn.
5. Chỉ trả về JSON chứa danh sách "new_assets".

OUTPUT SCHEMA:
{
  "new_assets": [
    { "type": "keyword_from_list", "polygon": [[x1,y1], [x2,y2], ...] }
  ]
}
```