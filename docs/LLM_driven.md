# PROPOSAL: CÔNG CỤ QUY HOẠCH KCN TƯƠNG TÁC (LLM-DRIVEN)

**Tên dự án đề xuất:** SmartPlan AI - Design by Conversation
**Ngày:** 11/12/2025
**Phiên bản:** 1.0

---

## 1. TẦM NHÌN & THAY ĐỔI CỐT LÕI (VISION & PIVOT)

Chúng tôi đề xuất chuyển dịch mô hình phát triển sản phẩm từ **"Tối ưu hóa Toán học" (Hard Optimization)** sang **"Thiết kế Tạo sinh Hội thoại" (Conversational Generative Design)**.

| Đặc điểm | Cách tiếp cận Cũ (Optimization-First) | Cách tiếp cận Mới (Interaction-First) |
| :--- | :--- | :--- |
| **Trọng tâm** | Giải bài toán cực đại hóa lợi nhuận (MILP/GA). | Tương tác người dùng và tính linh hoạt. |
| **Vai trò User** | Thụ động (Chờ kết quả). | Chủ động (Ra lệnh, chọn mẫu, chỉnh sửa). |
| **Vai trò AI** | "Kỹ sư tính toán" (Solver). | "Trợ lý thiết kế" (Copilot/Coder). |
| **Kết quả** | Khô cứng, tối ưu về số liệu nhưng thiếu thẩm mỹ. | Có cấu trúc rõ ràng, thẩm mỹ, dễ kiểm soát. |

---

## 2. QUY TRÌNH NGƯỜI DÙNG (USER JOURNEY)

Hệ thống hoạt động theo quy trình 4 bước đơn giản hóa, loại bỏ rào cản kỹ thuật cho người dùng.

### Bước 1: Khởi tạo (Minimal Input)
* **Hành động:** Người dùng tải lên file (CAD/Shapefile/GeoJSON) chỉ chứa duy nhất **Ranh giới khu đất (Boundary)**.
* **Hệ thống:** Hiển thị lô đất trên nền bản đồ vệ tinh/quy hoạch.

### Bước 2: Chọn "Khung xương" (Select Road Skeleton)
Thay vì tự vẽ, người dùng chọn các mẫu quy hoạch (Typologies) được định nghĩa sẵn.
* **Template A - Trục Trung Tâm (Spine):** Trục đường lớn giữa đất, nhánh xương cá 2 bên.
* **Template B - Bàn Cờ (Grid):** Lưới đường vuông góc (kiểu Mỹ/Âu).
* **Template C - Vành Đai (Loop):** Đường chạy vòng quanh biên, công trình ở giữa.
* **Template D - Chữ Thập (Cross):** Hai trục chính cắt nhau tại tâm.

> *Ngay khi chọn, LLM tự động tính toán và ướm (fit) khung đường vào hình dáng đất.*

### Bước 3: Tương tác & Tinh chỉnh (Conversational Interaction)
Người dùng tinh chỉnh thiết kế thông qua giao diện Chat hoặc Click-and-Drag.
* **Đặt Cổng:** Click chọn vị trí cổng trên biên đất -> Hệ thống tự nắn đường trục nối vào cổng.
* **Ra lệnh bằng lời (Prompting):**
    * *"Mở rộng đường trục chính lên 40m."*
    * *"Xoay toàn bộ lưới đường 15 độ song song với cạnh phía Bắc."*
    * *"Thêm vòng xoay (roundabout) tại giao lộ trung tâm."*

### Bước 4: Lấp đầy & Hoàn thiện (Auto-Fill)
* **Hành động:** Người dùng bấm "Hoàn thiện".
* **Hệ thống:**
    1.  Xác định các ô đất trống (Super-blocks) tạo bởi mạng lưới đường.
    2.  Tự động chia lô (Subdivision) bên trong các ô đất đó theo kích thước module.
    3.  Biến đổi các phần đất thừa/méo ở góc thành công viên cây xanh.

---

## 3. KIẾN TRÚC KỸ THUẬT (TECHNICAL ARCHITECTURE)

Loại bỏ các Solver phức tạp (OR-Tools, Pymoo), chuyển sang mô hình **LLM Code Interpreter**.

### Core Engine
* **Model:** GPT-4o hoặc Claude 3.5 Sonnet (có khả năng viết code mạnh).
* **Ngôn ngữ thực thi:** Python (với các thư viện `shapely`, `networkx`, `numpy`).

### Cơ chế hoạt động (The Loop)
1.  **Input:** User Prompt + Dữ liệu hình học (JSON).
2.  **Reasoning (LLM):** LLM phân tích yêu cầu -> Viết đoạn code Python để xử lý hình học (Ví dụ: dùng `shapely` để offset đường, dùng `split` để chia lô).
3.  **Execution (Sandbox):** Server chạy đoạn code Python đó trong môi trường an toàn.
4.  **Output:** Trả về kết quả hình học (GeoJSON/DXF) để hiển thị lên Frontend.

### Ví dụ Prompting
> **User:** "Chia khu đất này thành lưới bàn cờ."
>
> **System (LLM suy nghĩ):**
> 1.  Đọc polygon đầu vào.
> 2.  Lấy bounding box.
> 3.  Tạo các đường dọc/ngang cách nhau 100m.
> 4.  Cắt (intersection) các đường này với polygon đất.
> 5.  Trả về danh sách các LineString.

---

## 4. TẠI SAO PHƯƠNG ÁN NÀY KHẢ THI? (WHY THIS WORKS)

1.  **Dễ phát triển (Faster Time-to-Market):**
    * Không cần mô hình toán học phức tạp.
    * Chỉ cần tập trung viết Prompt và xây dựng bộ thư viện hàm hình học cơ bản (`draw_road`, `buffer`, `split`).
2.  **Linh hoạt tuyệt đối (Flexibility):**
    * Giải quyết được các yêu cầu "lạ" của khách hàng mà thuật toán cứng không làm được (ví dụ: "Vẽ đường hình tròn", "Tạo hồ nước ở giữa").
3.  **Thẩm mỹ cao (Aesthetics):**
    * Kết quả dựa trên các Template do con người thiết kế trước (Human-curated), đảm bảo tính quy chuẩn và đẹp mắt ngay từ đầu.
4.  **Trải nghiệm người dùng (UX):**
    * Người dùng cảm thấy mình là "Kiến trúc sư trưởng", máy chỉ là trợ lý thực thi. Cảm giác kiểm soát sản phẩm cao hơn.

---

## 5. KẾT LUẬN & ĐỀ XUẤT TIẾP THEO

Đây là hướng đi **"Low-Code / No-Code Generative Design"**. Chúng ta biến quy trình quy hoạch phức tạp thành trò chơi lắp ghép Lego thông minh.

**Next Steps:**
1.  Xây dựng thư viện hàm Python cơ bản cho quy hoạch (Geometry Utils).
2.  Viết System Prompt cho LLM để đóng vai trò "Kỹ sư quy hoạch".
3.  Xây dựng UI MVP cho phép upload đất và chọn Template.