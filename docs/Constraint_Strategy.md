# BÁO CÁO KỸ THUẬT: CHIẾN LƯỢC XỬ LÝ RÀNG BUỘC TRONG TỐI ƯU HÓA QUY HOẠCH

## 1. Tổng quan

Trong hệ thống thiết kế tự động, các yêu cầu đầu vào không đồng nhất về tính chất. Để thuật toán hoạt động hiệu quả, chúng ta phân loại yêu cầu thành 3 nhóm chính dựa trên cách thức xử lý trong vòng đời thuật toán:

1. **Ràng buộc Vật lý (Fixed Physical Constraints):** Dữ liệu đầu vào cố định.
2. **Ràng buộc Cứng (Hard Constraints):** Luật lệ bắt buộc.
3. **Ràng buộc Mềm (Soft Constraints):** Mong muốn tối ưu.

---

## 2. Chi tiết từng loại Ràng buộc

### Loại 1: Ràng buộc Vật lý (Fixed Context) - "Bộ Khung"

Đây là các yếu tố địa lý hoặc hạ tầng có sẵn không thể thay đổi (ví dụ: Tọa độ đường chính có sẵn, ranh giới khu đất, sông hồ, địa hình).

- **Vai trò:** Định hình không gian làm việc (Workspace) trước khi thuật toán chạy.
- **Phương pháp xử lý:** **Tiền xử lý (Pre-processing)**.
- **Kỹ thuật:**
  - **Boolean Operations:** Sử dụng phép cắt (`Difference`) để loại bỏ diện tích đường/sông ra khỏi quỹ đất xây dựng.
  - **Anchoring (Mỏ neo):** Sử dụng các tọa độ này làm điểm gieo (Seed points) hoặc điểm kết nối gốc cho thuật toán sinh đường nội bộ.
- **Ví dụ:** *Input là tọa độ trục đường chính → Hệ thống tạo vùng đệm (buffer) cho đường và trừ đi khỏi tổng diện tích đất trước khi chia lô.*

### Loại 2: Ràng buộc Cứng (Hard Constraints) - "Luật Lệ"

Đây là các quy chuẩn xây dựng hoặc pháp lý mang tính chất nhị phân (Đúng/Sai). Một giải pháp vi phạm dù chỉ một lỗi nhỏ cũng bị coi là vô giá trị (Infeasible).

- **Vai trò:** Đảm bảo tính hợp lệ (Validity) của giải pháp.
- **Phương pháp xử lý:** **Bộ lọc (Filtering) hoặc Sửa lỗi (Repair)**.
- **Kỹ thuật:**
  - **Veto (Phủ quyết):** Nếu `check_validity() == False` → Loại bỏ ngay lập tức, gán điểm phạt vô cực.
  - **Instant Repair:** Nếu vi phạm nhỏ (ví dụ lấn ranh 1m), dùng thuật toán hình học cắt gọt ngay lập tức để ép vào khuôn khổ.
- **Ví dụ:** *Diện tích lô đất tối thiểu phải là 1000m². Nếu AI sinh ra lô 999m² → Xóa bỏ hoặc gộp với lô bên cạnh.*

### Loại 3: Ràng buộc Mềm (Soft Constraints) - "Mong Muốn"

Đây là các yêu cầu định tính từ phía người dùng (User Preferences), mang tính chất "tốt hơn" hoặc "tệ hơn". Chúng quyết định chất lượng của phương án.

- **Vai trò:** Định hướng tối ưu hóa (Optimization) để tìm ra phương án tốt nhất.
- **Phương pháp xử lý:** **Hàm mục tiêu (Objective Function) & Trọng số (Weights)**.
- **Kỹ thuật:**
  - **Scoring (Chấm điểm):** Quy đổi các đặc tính hình học thành điểm số.
  - **Weighted Sum:** Tổng hợp điểm số dựa trên thanh trượt ưu tiên của User (ví dụ: Ưu tiên kinh tế 70%, Cây xanh 30%).
- **Ví dụ:** *User muốn các lô đất "vuông vắn". Lô hình chữ nhật được +10 điểm, lô hình thang được +5 điểm (vẫn chấp nhận nhưng điểm thấp hơn).*

---

## 3. Quy trình tích hợp (Workflow Integration)

Để hệ thống hoạt động trơn tru, 3 loại ràng buộc này phải được áp dụng theo trình tự phễu lọc như sau:

| Bước | Hành động | Loại Ràng buộc áp dụng | Mục đích |
|:-----|:----------|:-----------------------|:---------|
| **B1. Input** | **Cắt gọt (Carving)** | **Fixed Physical (Loại 1)** | Chuẩn bị "đất sạch" để xây dựng, đảm bảo kết nối hạ tầng có sẵn. |
| **B2. Generate** | **Sinh phương án** | *(Thuật toán ngẫu nhiên)* | Tạo ra hàng loạt phương án sơ bộ. |
| **B3. Validate** | **Kiểm tra (Check)** | **Hard Constraints (Loại 2)** | Loại bỏ "rác", chỉ giữ lại các phương án đúng luật. |
| **B4. Evaluate** | **Chấm điểm (Score)** | **Soft Constraints (Loại 3)** | Xếp hạng các phương án hợp lệ để tìm ra cái User thích nhất. |

---

## 4. Kết luận & Kiến nghị

### 4.1. Giao diện (UI)

Cần tách biệt rõ ràng khu vực nhập liệu:

- Input tọa độ (Loại 1) và Luật xây dựng (Loại 2) nên nằm trong phần **Settings/Config** (User không được tùy tiện chỉnh sửa sai luật).
- Các mong muốn (Loại 3) nên nằm ở dạng **Sliders/Dials** để User tự do khám phá các phương án khác nhau.

### 4.2. Hiệu năng

Xử lý triệt để Loại 1 (Cắt đất) ngay từ đầu sẽ giúp thuật toán chạy nhanh hơn 50-70% so với việc để AI tự mò mẫm và check lại.
