Mô hình Agent + MCP (Mới):
User <-> Agent <-> MCP Servers (Đọc file, Chạy toán, Render)
Agent tự chat với MCP: "Chạy thử -> Lỗi -> Sửa tham số -> Chạy lại -> Thành công" -> User (Nhận kết quả hoàn chỉnh).
🛠 Cơ cấu MCP Server đề xuất
Geometry & IO MCP Server:
Công cụ: read_dxf, write_dxf, rasterize_image (tạo ảnh preview), check_geometry_validity.
Nhiệm vụ: Xử lý file nặng, chuyển đổi định dạng.
Optimization Solver MCP Server:
Công cụ: solve_partitioning, solve_road_network.
Nhiệm vụ: Chứa logic toán học (CP Model), thuật toán di truyền, v.v.



Giai đoạn 1: Tiếp nhận & Tri giác (Perception)
Thay vì chờ dữ liệu được "đút" vào mồm (tiền xử lý thủ công), Agent chủ động gọi công cụ để "nhìn" và hiểu dữ liệu.
User Input: Người dùng upload file CAD (.dxf) và chat: "Chia lô đất này thành các nền 100m2, đường 7.5m".
Tool Call (MCP IO):
Agent nhận thấy có file đính kèm. Nó gọi tool read_dxf_structure từ MCP Server (IO).
MCP Server: Đọc file binary, lọc các layer không cần thiết, trích xuất tọa độ ranh giới (Boundary) và vùng cấm (Obstacles).
Data Ingestion: Agent nhận về dữ liệu GeoJSON sạch từ MCP và lưu vào "Short-term Memory" (Bộ nhớ ngắn hạn) của cuộc hội thoại.
Giai đoạn 2: Suy luận & Lập kế hoạch (Reasoning & Planning)
Agent đóng vai trò là "Kỹ sư trưởng", phân tích yêu cầu và lên kế hoạch thực hiện.
Context Analysis: Agent phân tích yêu cầu:
Mục tiêu: Phân lô (Partitioning).
Ràng buộc cứng: Diện tích = 100m2.
Ràng buộc mềm: Đường giao thông = 7.5m.
Strategy Formulation: Agent tự lên kịch bản:
"Dữ liệu hình học có vẻ phức tạp, mình nên thử chia lưới sơ bộ trước rồi mới chạy tối ưu hóa chi tiết."
Construct Payload: Agent tạo ra tham số đầu vào chuẩn xác cho thuật toán CP.
Giai đoạn 3: Thực thi & Tự sửa lỗi (Execution & Self-Correction)
Đây là bước quan trọng nhất tạo nên sự khác biệt của Agent. Nó diễn ra trong vòng lặp kín, người dùng không cần can thiệp.
Tool Call (MCP Solver): Agent gọi tool optimize_land_partition trên MCP Server (Solver) với các tham số đã chuẩn bị.
The Solver Loop (MCP Side): Server chạy thuật toán (OR-Tools/Shapely).
Agent Evaluation (Vòng lặp tự chủ):
Trường hợp 1 (Thành công): MCP trả về danh sách tọa độ các lô đất. Agent kiểm tra thấy hợp lý $\rightarrow$ Chuyển sang Giai đoạn 4.
Trường hợp 2 (Lỗi/Không khả thi): MCP trả về lỗi: Infeasible: Road width consumes too much area.
LLM cũ: Báo lỗi ngay cho khách hàng.
Agent mới: Tự suy luận "Đường 7.5m quá lớn cho mảnh đất này. Mình sẽ thử giảm xuống 6m (mức tối thiểu cho phép) và chạy lại."
Agent tự động gọi lại tool optimize_land_partition với road_width = 6.0.
Giai đoạn 4: Tổng hợp & Trình bày (Synthesis & Output)
Agent sử dụng các công cụ render để biến dữ liệu số thành sản phẩm trực quan.
Visual Generation:
Agent gọi tool render_layout_to_image (từ MCP IO) để tạo ảnh xem trước (.png) có tô màu các lô đất.
Agent gọi tool export_dxf để tạo file bản vẽ kỹ thuật mới.
Final Response: Agent tổng hợp thông tin và trả lời người dùng:
"Tôi đã hoàn thành phương án. Lưu ý: Do đất hẹp, tôi đã tự động điều chỉnh đường nội bộ từ 7.5m xuống 6m để đảm bảo đủ diện tích các lô. Dưới đây là bản vẽ và thông số chi tiết..."

