Cơ chế hoạt động của phần Core Engine theo mô hình "Nhạc trưởng & Kỹ sư" (Orchestrator-Solver Model):

1. Phân chia vai trò
🧠 LLM (The Brain/Nhạc trưởng): Chịu trách nhiệm hiểu ngữ nghĩa, điều phối luồng đi, xử lý logic nghiệp vụ và giao tiếp với con người. LLM không trực tiếp tính toán hình học.

⚙️ CP Module (The Muscle/Kỹ sư): Chịu trách nhiệm tính toán toán học, giải quyết các ràng buộc hình học (Geometry) và tối ưu hóa (Optimization) chính xác tuyệt đối. CP hoạt động như một "hộp đen" (black-box) xử lý dữ liệu.

2. Quy trình "Bắt tay" (The Handshake Loop)
Quy trình diễn ra theo vòng lặp khép kín 4 bước:

Dịch (Translation):

LLM nhận yêu cầu tự nhiên (VD: "Tránh kho xăng 200m").

LLM chuyển đổi yêu cầu thành tham số kỹ thuật chuẩn (JSON) để gọi hàm (Function Calling).

Giải (Execution):

CP Module nhận JSON, chạy thuật toán (MILP/GeoPandas).

CP trả về kết quả thô (số liệu, tọa độ) hoặc trạng thái lỗi (nếu bài toán vô nghiệm).

Hiểu (Interpretation):

LLM đọc kết quả thô từ CP.

LLM so sánh với yêu cầu ban đầu để đánh giá: Thành công hay Thất bại.

Quyết định (Reasoning & Action):

Nếu thành công: LLM ra lệnh xuất bản vẽ và báo cáo cho người dùng.

Nếu thất bại (Xung đột): LLM tự động suy luận nguyên nhân (VD: "Quá chật chội"), đề xuất phương án nới lỏng ràng buộc và hỏi ý kiến người dùng.

3. Ưu điểm cốt lõi
Cơ chế này khắc phục được điểm yếu chết người của từng công nghệ riêng lẻ:

Loại bỏ sự "ảo giác" (hallucination) của AI vì mọi con số đều do CP tính.

Loại bỏ sự "cứng nhắc" của thuật toán truyền thống vì LLM giúp linh hoạt trong việc nhập liệu và xử lý tình huống phát sinh.