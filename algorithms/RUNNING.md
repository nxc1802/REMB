# Dự án Algorithm Testing - Đang Chạy

## Trạng Thái Hiện Tại

### ✅ Backend (FastAPI) - ĐANG CHẠY
- **URL**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs  
- **Health**: http://localhost:8000/health
- **Trạng thái**: Application startup complete

### ✅ Frontend (Streamlit) - ĐANG CHẠY
- **URL**: http://localhost:8502
- **Trạng thái**: Ready to use
- **Network**: http://192.168.2.9:8502

## Cách Sử Dụng

### Bước 1: Mở Streamlit UI
Truy cập: http://localhost:8502

### Bước 2: Cấu hình Parameters (Sidebar)
- Min Spacing: 20m
- Max Spacing: 30m  
- Angle Range: 0-90°
- Lot Width: 5-8m
- Population: 50
- Generations: 100

### Bước 3: Input Tab
Chọn **"Use Sample Data"** để test nhanh

### Bước 4: Run Optimization Tab
Nhấn **"🚀 Run Full Pipeline"**

Chờ 30-60 giây để thuật toán chạy.

### Bước 5: Results Tab
Xem kết quả:
- Summary statistics
- Stage 1: Grid Optimization visualization
- Stage 2: Block Subdivision visualization
- Download GeoJSON results

## Ghi Chú Kỹ Thuật

### Ports Sử Dụng
- Backend: 8000 (default port)
- Frontend: 8502 (tránh conflict với service trên 8501)

### Đã Fix
1. Import errors (relative → absolute imports)
2. Folium version conflict (0.15.1 → 0.14.0)
3. Port configuration trong frontend (8001 → 8000)

### Dependencies Installed
**Backend**:
- FastAPI 0.104.1
- DEAP 1.4.1
- OR-Tools 9.8.3296
- Shapely 2.0.2

**Frontend**:
- Streamlit 1.29.0
- Plotly 5.18.0
- Pandas 2.1.4

## Dừng Services

```bash
# Tìm và kill backend process
lsof -i :8000
kill -9 <PID>

# Tìm và kill frontend process
lsof -i :8502
kill -9 <PID>
```

# Restart Services

# Terminal 1: Backend
# Kill existing backend process
lsof -i :8000 | awk 'NR!=1 {print $2}' | xargs kill -9
cd /Volumes/WorkSpace/Project/REMB/algorithms/backend
../../venv/bin/uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
# Kill existing frontend process
lsof -i :8502 | awk 'NR!=1 {print $2}' | xargs kill -9
cd /Volumes/WorkSpace/Project/REMB/algorithms/frontend
../../venv/bin/streamlit run app.py --server.port 8502
