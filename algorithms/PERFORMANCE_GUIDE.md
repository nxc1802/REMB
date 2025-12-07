# Hướng Dẫn Tối Ưu Hiệu Suất

## 📊 Các Thông Số Ảnh Hưởng Đến Thời Gian Chạy

### 1. **Population Size** (Kích thước quần thể)
- **Phạm vi**: 20 - 200
- **Mặc định**: 50
- **Ảnh hưởng**: 
  - ⬆️ Tăng: Thuật toán khám phá nhiều giải pháp hơn → Kết quả tốt hơn nhưng **chậm hơn nhiều**
  - ⬇️ Giảm: Ít giải pháp được thử → Nhanh nhưng có thể bỏ lỡ giải pháp tối ưu
- **Độ phức tạp**: `O(population_size × generations)`

### 2. **Generations** (Số thế hệ)
- **Phạm vi**: 50 - 500
- **Mặc định**: 50
- **Ảnh hưởng**:
  - ⬆️ Tăng: Thuật toán tiến hóa lâu hơn → Hội tụ tốt hơn nhưng **tốn nhiều thời gian**
  - ⬇️ Giảm: Kết thúc sớm → Nhanh nhưng có thể chưa tối ưu
- **Độ phức tạp**: `O(population_size × generations)`

### 3. **OR-Tools Time/Block** (Thời gian tối ưu mỗi block)
- **Phạm vi**: 0.1 - 60.0 giây
- **Mặc định**: 5.0 giây
- **Ảnh hưởng**:
  - ⬆️ Tăng: OR-Tools có nhiều thời gian tìm giải pháp tốt hơn cho mỗi block
  - ⬇️ Giảm: OR-Tools dừng sớm, có thể chưa tối ưu
- **Lưu ý**: Thời gian này được nhân với số lượng blocks

### 4. **Kích Thước Đất** (Gián tiếp)
- Đất lớn → Nhiều blocks → Tổng thời gian tăng tuyến tính
- Công thức ước lượng số blocks: `(Area / (spacing²))`

---

## ⚡ Các Preset Cấu Hình Được Khuyến Nghị

### 🚀 **Kết Quả Nhanh Nhất** (Test/Preview)
**Thời gian ước tính**: 30 giây - 2 phút

```
Population Size:      20
Generations:          50
OR-Tools Time/Block:  0.5s
Spacing Min/Max:      25-35m
```

**Khi nào dùng**:
- ✅ Test nhanh với đất mới
- ✅ Xem trước kết quả sơ bộ
- ✅ Điều chỉnh parameters
- ❌ **KHÔNG** dùng cho kết quả cuối cùng

**Trade-offs**:
- ✅ Cực kỳ nhanh
- ⚠️ Chất lượng thấp
- ⚠️ Có thể không tìm được giải pháp tốt

---

### ⚖️ **Kết Quả Cân Bằng** (Recommended)
**Thời gian ước tính**: 3-8 phút

```
Population Size:      50
Generations:          50-75
OR-Tools Time/Block:  3.0-5.0s
Spacing Min/Max:      20-30m
```

**Khi nào dùng**:
- ✅ **Sử dụng hàng ngày** (khuyến nghị)
- ✅ Đất có kích thước trung bình (< 5 ha)
- ✅ Cần kết quả tốt trong thời gian chấp nhận được
- ✅ Đủ tốt cho hầu hết các trường hợp

**Trade-offs**:
- ✅ Cân bằng giữa tốc độ và chất lượng
- ✅ Kết quả đủ tốt (80-90% tối ưu)
- ✅ Thời gian chấp nhận được

---

### 🏆 **Kết Quả Tốt Nhất** (Production Quality)
**Thời gian ước tính**: 10-30 phút

```
Population Size:      100-150
Generations:          100-150
OR-Tools Time/Block:  10.0-15.0s
Spacing Min/Max:      20-30m
```

**Khi nào dùng**:
- ✅ Dự án thực tế quan trọng
- ✅ Cần kết quả tối ưu nhất có thể
- ✅ Có thời gian chờ đợi
- ✅ Đất lớn, phức tạp

**Trade-offs**:
- ✅ Chất lượng cao nhất (95-99% tối ưu)
- ✅ Khám phá nhiều giải pháp
- ⚠️ Tốn thời gian
- ⚠️ Có thể timeout nếu đất quá lớn

---

### 🔥 **Aggressive Optimization** (Maximum Quality)
**Thời gian ước tính**: 30-60+ phút

```
Population Size:      200
Generations:          200-300
OR-Tools Time/Block:  20.0-30.0s
Spacing Min/Max:      20-30m
```

**Khi nào dùng**:
- ✅ Dự án cực kỳ quan trọng
- ✅ Muốn kết quả **tốt nhất tuyệt đối**
- ✅ Có thể để chạy qua đêm
- ⚠️ Chỉ với đất nhỏ/trung bình

**Trade-offs**:
- ✅ Gần như tối ưu toàn cục
- ⚠️ Rất chậm
- ⚠️ Diminishing returns (cải thiện ít so với thời gian tăng)

---

## 📈 Bảng So Sánh Nhanh

| Preset | Population | Generations | OR-Tools Time | Thời gian | Chất lượng | Use Case |
|--------|------------|-------------|---------------|-----------|------------|----------|
| 🚀 Fastest | 20 | 50 | 0.5s | 0.5-2 min | ⭐⭐ | Test/Preview |
| ⚖️ Balanced | 50 | 50-75 | 3-5s | 3-8 min | ⭐⭐⭐⭐ | **Recommended** |
| 🏆 Best | 100-150 | 100-150 | 10-15s | 10-30 min | ⭐⭐⭐⭐⭐ | Production |
| 🔥 Maximum | 200 | 200-300 | 20-30s | 30-60+ min | ⭐⭐⭐⭐⭐ | Critical Projects |

---

## 💡 Mẹo Tối Ưu

### 1. **Điều chỉnh theo kích thước đất**

```
Đất nhỏ (< 1 ha):
  → Dùng preset "Best" hoặc "Maximum"
  → Thời gian chấp nhận được

Đất trung bình (1-5 ha):
  → Dùng preset "Balanced"
  → Tăng Generations lên 100 nếu cần

Đất lớn (> 5 ha):
  → Dùng preset "Fastest" hoặc "Balanced"
  → KHÔNG dùng "Maximum" (sẽ quá chậm)
```

### 2. **Tăng dần theo bước**

Thay vì nhảy thẳng lên "Maximum", hãy:
1. Chạy "Fastest" để xem kết quả sơ bộ
2. Chạy "Balanced" để có kết quả tốt
3. Nếu cần, chạy "Best" vào cuối

### 3. **OR-Tools Time Strategy**

```
Block đơn giản (hình chữ nhật):
  → 0.5-2.0s là đủ

Block phức tạp (hình bất quy tắc):
  → 5.0-10.0s
  
Block cực kỳ phức tạp:
  → 15.0-30.0s
```

### 4. **Parallel Testing (Nếu có nhiều máy)**

Chạy song song nhiều cấu hình:
- Machine 1: Balanced (50/75/5s)
- Machine 2: Best (100/100/10s)
- Machine 3: Maximum (200/200/20s)

→ Chọn kết quả tốt nhất

---

## 🎯 Công Thức Ước Lượng Thời Gian

```python
# Rough estimate (seconds)
time_estimate = (population_size × generations × 0.5) + (num_blocks × ortools_time)

# Where:
num_blocks ≈ land_area / (spacing_avg²)

# Example: Đất 10,000 m², spacing 25m, pop=50, gen=75, ort=5s
num_blocks ≈ 10000 / (25²) = 16 blocks
time_estimate = (50 × 75 × 0.5) + (16 × 5) = 1875 + 80 = ~1955s ≈ 33 phút
```

---

## ⚠️ Lưu Ý Quan Trọng

1. **Timeout 10 phút**: 
   - Frontend có timeout 600s (10 phút)
   - Nếu cần chạy lâu hơn, tăng timeout trong `app.py`

2. **Diminishing Returns**:
   - Tăng từ 50 → 100 generations: Cải thiện ~15-20%
   - Tăng từ 100 → 200 generations: Cải thiện ~5-10%
   - Tăng từ 200 → 500 generations: Cải thiện ~1-5%

3. **Memory Usage**:
   - Population lớn (>150) có thể tốn nhiều RAM
   - Đất rất lớn với population cao: risk of OOM

4. **Stage 1 vs Stage 2**:
   - Stage 1 (NSGA-II): Chi phối thời gian với nhiều generations
   - Stage 2 (OR-Tools): Chi phối với đất lớn (nhiều blocks)

---

## 🔧 Troubleshooting

### Timeout sau 10 phút?
→ Giảm Population hoặc Generations
→ Hoặc tăng timeout trong code

### Kết quả chưa tốt?
→ Tăng Generations (cheaper than population)
→ Tăng OR-Tools time/block

### Muốn nhanh hơn nữa?
→ Tăng Spacing Min/Max (ít blocks hơn)
→ Giảm OR-Tools time xuống 0.5-1.0s

### Đất rất lớn?
→ Chia thành nhiều phần nhỏ
→ Hoặc tăng spacing để giảm số blocks

---

## 📝 Recommended Workflow

```
1. Start: Chạy FASTEST preset
   → Xác nhận input đúng
   → Xem kết quả sơ bộ
   
2. Iterate: Chạy BALANCED preset  
   → Điều chỉnh spacing, lot width
   → Xem kết quả có chấp nhận được không
   
3. Finalize: Chạy BEST preset
   → Với parameters đã điều chỉnh
   → Export DXF cho production
   
4. Optional: Chạy MAXIMUM nếu cực kỳ cần thiết
```

---

## 🎓 Kết Luận

**TL;DR - Quick Answer:**
- **Test nhanh**: Pop=20, Gen=50, ORT=0.5s
- **Khuyến nghị**: Pop=50, Gen=75, ORT=5s ⭐
- **Tốt nhất**: Pop=150, Gen=150, ORT=15s
