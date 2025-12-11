# SmartPlan AI - Running Commands

## Backend (Port 8002)

```bash
cd /Volumes/WorkSpace/Project/REMB/smartplan_ai/backend
lsof -ti :8002 | xargs kill -9 2>/dev/null
export $(cat ../.env | xargs)
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

## Frontend (Port 3000)

```bash
cd /Volumes/WorkSpace/Project/REMB/smartplan_ai/frontend
lsof -ti :3000 | xargs kill -9 2>/dev/null
npm run dev
```

## URLs

- Backend API: http://localhost:8002
- API Docs: http://localhost:8002/docs
- Frontend: http://localhost:3000
