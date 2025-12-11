# Running SmartPlan AI v3.0

## Quick Start

### Backend (FastAPI + MegaLLM)
```bash
# Kill port 8003 if running
lsof -ti:8003 | xargs kill -9 || true

cd smartplan_ai_v3/backend
uvicorn main:app --reload --port 8003
```
*API Docs: http://localhost:8003/docs*

### Frontend (Next.js)
```bash
# Kill port 3000 if running
lsof -ti:3000 | xargs kill -9 || true

cd smartplan_ai_v3/frontend
npm run dev
```
*App URL: http://localhost:3000*

## Test Flow (Full End-to-End)

1. **Set Boundary**: Load sample data or upload DXF
2. **Select Block**: Click on a block in the map
3. **Chat**: Ask AI to generate assets (e.g., "Add a warehouse")
4. **Finalize**: Click "Finalize Infrastructure" to route utilities
