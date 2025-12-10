Chào bạn, đây là phần đi sâu chi tiết vào các kỹ thuật **tối ưu hóa thẩm mỹ (Aesthetic Optimization)** kèm theo các đoạn code Python thực tế sử dụng thư viện `Shapely` và `NumPy` mà bạn có thể tích hợp ngay vào dự án.

Chúng ta sẽ tập trung vào 3 giải pháp cốt lõi: **Kiểm soát hình học**, **Cắt gọt trực giao (Orthogonal Slicing)**, và **Xử lý phần dư thông minh**.

-----

### 1\. Phương pháp 1: Kiểm soát Hình học (Geometric Regularization)

**Mục tiêu:** Loại bỏ các lô đất có hình dạng "kỳ dị" (quá dẹt, quá méo) ngay từ bước sinh phương án hoặc dùng làm hàm mục tiêu để phạt điểm.

**Chỉ số kỹ thuật:**

1.  **Rectangularity (Độ đầy đặn):** Tỷ lệ diện tích lô đất so với hình chữ nhật bao quanh nó (Oriented Bounding Box - OBB). Giá trị càng gần 1.0 càng vuông.
2.  **Aspect Ratio (Tỷ lệ cạnh):** Tỷ lệ giữa chiều dài và chiều rộng.

**Đoạn Code Tối ưu:**

```python
import numpy as np
from shapely.geometry import Polygon

def analyze_shape_quality(polygon):
    """
    Trả về điểm số thẩm mỹ và trạng thái hợp lệ của lô đất.
    """
    if polygon.is_empty or not polygon.is_valid:
        return 0.0, False

    # 1. Tính OBB (Oriented Bounding Box) - Hình chữ nhật bao quanh nhỏ nhất
    obb = polygon.minimum_rotated_rectangle
    
    # Tính độ vuông vắn (Rectangularity)
    # Nếu polygon là hình chữ nhật, tỷ số = 1.0. Nếu là tam giác, tỷ số ~ 0.5
    rectangularity = polygon.area / obb.area
    
    # 2. Tính Tỷ lệ cạnh (Aspect Ratio) từ OBB
    x, y = obb.exterior.coords.xy
    # Tính độ dài 2 cạnh kề nhau của OBB
    edge_1 = np.hypot(x[1] - x[0], y[1] - y[0])
    edge_2 = np.hypot(x[2] - x[1], y[2] - y[1])
    
    if edge_1 == 0 or edge_2 == 0: return 0.0, False
    
    width, length = sorted([edge_1, edge_2])
    aspect_ratio = length / width
    
    # --- CÁC LUẬT RÀNG BUỘC (HARD CONSTRAINTS) ---
    is_valid = True
    
    # Luật 1: Phải tương đối vuông (chấp nhận méo nhẹ do vạt góc)
    if rectangularity < 0.75: 
        is_valid = False 
        
    # Luật 2: Không được quá dẹt (ví dụ: dài gấp 4 lần rộng là xấu)
    if aspect_ratio > 4.0:
        is_valid = False
        
    # Luật 3: Diện tích tối thiểu (để tránh lô vụn)
    if polygon.area < 1000: # m2
        is_valid = False

    # Điểm thưởng cho lô đất đẹp (để dùng cho hàm mục tiêu)
    score = (rectangularity * 0.7) + ((1.0 / aspect_ratio) * 0.3)
    
    return score, is_valid

# Ví dụ sử dụng trong vòng lặp chia lô
# for lot in generated_lots:
#     score, valid = analyze_shape_quality(lot)
#     if not valid:
#         # Đưa vào danh sách "Đất cây xanh/Kỹ thuật" thay vì "Đất thương phẩm"
#         move_to_leftover(lot)
```

-----

### 2\. Phương pháp 2: Cắt gọt Trực giao (Orthogonal Alignment)

**Mục tiêu:** Thay vì dùng Voronoi ngẫu nhiên (tạo ra các cạnh xiên xẹo), chúng ta ép buộc các đường cắt phải **vuông góc** với trục đường chính hoặc cạnh dài nhất của Block mẹ.

**Thuật toán:**

1.  Xác định "Cạnh chủ" (Dominant Edge) của Block mẹ (thường là cạnh giáp đường).
2.  Tạo vector vuông góc với Cạnh chủ.
3.  Thực hiện chia lô theo vector này.

**Đoạn Code Tối ưu:**

```python
from shapely.affinity import rotate, translate

def get_dominant_edge_vector(polygon):
    """Tìm vector chỉ phương của cạnh dài nhất (thường là mặt tiền)"""
    rect = polygon.minimum_rotated_rectangle
    x, y = rect.exterior.coords.xy
    
    # Lấy 3 điểm đầu để xác định 2 cạnh kề nhau
    p0 = np.array([x[0], y[0]])
    p1 = np.array([x[1], y[1]])
    p2 = np.array([x[2], y[2]])
    
    edge1_len = np.linalg.norm(p1 - p0)
    edge2_len = np.linalg.norm(p2 - p1)
    
    # Trả về vector đơn vị của cạnh dài nhất
    if edge1_len > edge2_len:
        vec = p1 - p0
    else:
        vec = p2 - p1
        
    return vec / np.linalg.norm(vec)

def orthogonal_slice(block, num_lots):
    """
    Chia block thành các lô song song, vuông góc với cạnh chính.
    Đây là kỹ thuật quan trọng nhất để tạo ra sự ngăn nắp.
    """
    # 1. Lấy hướng trục chính
    direction_vec = get_dominant_edge_vector(block)
    
    # Vector vuông góc (dùng để quét cắt)
    perp_vec = np.array([-direction_vec[1], direction_vec[0]])
    
    # 2. Xoay block về trục ngang để dễ tính toán (Optional nhưng recommended)
    # Ở đây ta dùng cách tạo đường cắt trực tiếp
    
    minx, miny, maxx, maxy = block.bounds
    # Tạo một đường thẳng dài bao trùm block
    diagonal = np.hypot(maxx-minx, maxy-miny)
    
    lots = []
    # Giả sử chia đều (trong thực tế bạn sẽ dùng OR-Tools để tính widths)
    # Ta cần tìm điểm bắt đầu và kết thúc dọc theo cạnh chính
    # (Phần này cần logic chiếu hình học phức tạp hơn một chút, 
    # dưới đây là mô phỏng cách dao cắt hoạt động)
    
    # ... Logic cắt (simplified) ...
    # Thay vì code cắt phức tạp, hãy áp dụng nguyên tắc:
    # "Luôn xoay vector cắt lệch 90 độ so với vector đường giao thông tiếp giáp"
    
    return lots # Trả về danh sách lô đã cắt vuông
```

-----

### 3\. Phương pháp 3: Xử lý phần dư (Leftover Management) - "Biến rác thành hoa"

**Mục tiêu:** Sau khi chia các lô vuông vắn, sẽ luôn còn lại các mẩu đất hình tam giác hoặc hình thang méo ở các góc cua. Thay vì cố ép nó thành đất ở (làm xấu bản vẽ và giảm giá trị), hãy tự động chuyển đổi nó thành **Tiện ích**.

**Chiến lược:**

  * Chạy thuật toán chia lô vuông vắn tối đa.
  * Phần diện tích còn lại (Difference) $\rightarrow$ Kiểm tra hình dáng.
  * Nếu `Rectangularity < 0.6` $\rightarrow$ Gán label `Cây xanh` hoặc `Bãi đỗ xe`.

**Đoạn Code Tối ưu quy trình:**

```python
def optimize_layout_w_leftovers(site_polygon, road_network):
    # 1. Tạo các Block lớn từ mạng lưới đường
    blocks = site_polygon.difference(road_network)
    
    final_commercial_lots = []
    final_green_spaces = []
    
    for block in blocks.geoms:
        # Bước A: Làm sạch hình học block (Simplify)
        clean_block = block.simplify(0.5, preserve_topology=True)
        
        # Bước B: Chia lô (Sử dụng thuật toán cắt trực giao ở trên)
        # Giả sử hàm subdivide_block trả về danh sách các lô
        raw_lots = subdivide_block_orthogonally(clean_block) 
        
        for lot in raw_lots:
            # Bước C: Đánh giá thẩm mỹ
            score, is_valid = analyze_shape_quality(lot)
            
            if is_valid:
                # Nếu lô đẹp -> Đất thương phẩm
                final_commercial_lots.append(lot)
            else:
                # Nếu lô quá méo/nhỏ -> Chuyển thành đất cây xanh
                # Đây là bước "Làm đẹp" bản vẽ
                final_green_spaces.append(lot)
                
    return final_commercial_lots, final_green_spaces
```

### 4\. Tích hợp vào OR-Tools (Hàm mục tiêu nâng cao)

Nếu bạn đang dùng `CP-SAT` solver của Google OR-Tools (như trong context cũ), bạn có thể sửa hàm mục tiêu để tối ưu sự đồng đều (Symmetry).

**Code OR-Tools (Logic):**

```python
# Thay vì chỉ Maximize(TotalArea), hãy thêm phạt sự chênh lệch
# Mục tiêu: Các lô nên có kích thước bằng nhau (Target Width)

# ... khai báo biến widths[i] ...

target_width = 15.0 # mét (Mặt tiền mong muốn)
deviations = []

for w in widths:
    # Tạo biến phụ để tính trị tuyệt đối: abs(w - target)
    diff = model.NewIntVar(0, 100, 'diff')
    
    # Mẹo OR-Tools để tính abs:
    # diff >= w - target  VÀ  diff >= target - w
    model.Add(diff >= w - int(target_width))
    model.Add(diff >= int(target_width) - w)
    
    deviations.append(diff)

# Hàm mục tiêu mới:
# Tối đa hóa diện tích NHƯNG Trừ điểm nặng nếu kích thước không đều
model.Maximize(sum(widths) * 100 - sum(deviations) * 50) 
```

### Tổng kết chiến lược

Để bản vẽ từ "Tối ưu tài chính (xấu)" trở thành "Tối ưu tổng thể (đẹp + hiệu quả)", bạn chỉ cần thực hiện thay đổi nhỏ trong luồng xử lý:

1.  **Input:** Xác định cạnh đường chính.
2.  **Process:** Chỉ cắt vuông góc với cạnh đường (Force 90 deg).
3.  **Filter:** Dùng hàm `analyze_shape_quality` để lọc các mảnh vỡ.
4.  **Post-Process:** Tô màu xanh (công viên) cho các mảnh vỡ đó thay vì cố gắng bán chúng.

Bản vẽ sẽ trông chuyên nghiệp hơn ngay lập tức vì sự ngăn nắp và có nhiều không gian xanh ở các góc ngã tư.