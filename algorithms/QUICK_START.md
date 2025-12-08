# 🚀 Quick Deployment Reference

## Local Testing

### Using Docker Compose (Recommended)
```bash
cd /Volumes/WorkSpace/Project/REMB/algorithms

# Build images
make build

# Start services
make up

# View logs
make logs

# Check health
make health

# Access services
# Backend:  http://localhost:8000
# Frontend: http://localhost:8501
# API Docs: http://localhost:8000/docs

# Stop services
make down
```

### Manual (Without Docker)
```bash
# Terminal 1: Backend
cd /Volumes/WorkSpace/Project/REMB/algorithms/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd /Volumes/WorkSpace/Project/REMB/algorithms/frontend
pip install -r requirements.txt
export API_URL=http://localhost:8000
streamlit run app.py --server.port 8501
```

---

## Production Deployment

### Backend → Hugging Face Spaces

```bash
cd /Volumes/WorkSpace/Project/REMB/algorithms/backend

# 1. Rename README for HF
cp README_HF.md README.md

# 2. Initialize git (if needed)
git init

# 3. Add HF remote (replace with your details)
git remote add hf https://huggingface.co/spaces/<USERNAME>/<SPACE_NAME>

# 4. Commit and push
git add .
git commit -m "Deploy to Hugging Face Spaces"
git push hf main

# 5. Monitor build at:
# https://huggingface.co/spaces/<USERNAME>/<SPACE_NAME>
```

**Your API will be at**: `https://<USERNAME>-<SPACE_NAME>.hf.space`

### Frontend → Streamlit Cloud

```bash
cd /Volumes/WorkSpace/Project/REMB/algorithms/frontend

# 1. Push to GitHub
git init
git remote add origin https://github.com/<USERNAME>/<REPO_NAME>.git
git add .
git commit -m "Initial commit"
git branch -M main
git push -u origin main

# 2. Go to Streamlit Cloud
# https://streamlit.io/cloud

# 3. Create new app:
# - Repository: <USERNAME>/<REPO_NAME>
# - Branch: main
# - Main file: app.py

# 4. Add secrets in Streamlit Cloud settings:
# API_URL = "https://<HF_USERNAME>-<SPACE_NAME>.hf.space"

# 5. Deploy!
```

**Your app will be at**: `https://<APP_NAME>.streamlit.app`

---

## Environment Variables

### Backend (.env or HF Secrets)
```bash
API_HOST=0.0.0.0
API_PORT=7860
CORS_ORIGINS=*
LOG_LEVEL=INFO
```

### Frontend (.env or Streamlit Secrets)
```bash
# Development
API_URL=http://localhost:8000

# Production
API_URL=https://<HF_USERNAME>-<SPACE_NAME>.hf.space
```

---

## Troubleshooting

### Docker Build Fails
```bash
# Test build locally
cd backend
docker build -t test .

# Check logs
docker logs <container_id>

# Run interactively
docker run -it test /bin/bash
```

### Frontend Can't Connect
1. Check `API_URL` environment variable
2. Verify backend is running
3. Check CORS settings in backend
4. Test backend directly: `curl <API_URL>/health`

### Port Already in Use
```bash
# Find process
lsof -i :8000
lsof -i :8501

# Kill process
kill -9 <PID>
```

---

## Testing Deployed Services

### Test Backend API
```bash
# Health check
curl https://<USERNAME>-<SPACE_NAME>.hf.space/health

# View API docs
open https://<USERNAME>-<SPACE_NAME>.hf.space/docs

# Test optimization endpoint
curl -X POST https://<USERNAME>-<SPACE_NAME>.hf.space/api/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "spacing_min": 20,
      "spacing_max": 30,
      "population_size": 20,
      "generations": 50
    },
    "land_plots": [{
      "type": "Polygon",
      "coordinates": [[[0,0],[100,0],[100,100],[0,100],[0,0]]]
    }]
  }'
```

### Test Frontend
1. Open `https://<APP_NAME>.streamlit.app`
2. Select "Sample" → "Rectangle 100x100"
3. Click "🚀 Run Optimization"
4. Wait for results
5. Download GeoJSON

---

## Useful Makefile Commands

```bash
make help           # Show all available commands
make build          # Build Docker images
make up             # Start services
make down           # Stop services
make logs           # View all logs
make logs-backend   # View backend logs only
make logs-frontend  # View frontend logs only
make restart        # Restart all services
make clean          # Stop and remove volumes
make test-backend   # Test backend container
make dev-backend    # Run backend without Docker
make dev-frontend   # Run frontend without Docker
make status         # Show service status
make health         # Check service health
```

---

## File Checklist

Before deploying, ensure these files exist:

**Backend**:
- [x] `Dockerfile`
- [x] `.dockerignore`
- [x] `requirements.txt` (with production deps)
- [x] `README_HF.md` (will become README.md)

**Frontend**:
- [x] `app.py` (with environment support)
- [x] `requirements.txt` (with python-dotenv)
- [x] `.streamlit/config.toml`

**Root**:
- [x] `docker-compose.yml`
- [x] `Makefile`
- [x] `.env.production` (template)
- [x] `DEPLOYMENT.md`
- [x] `README.md` (updated)

---

## Quick Links

- 📖 **Full Guide**: [DEPLOYMENT.md](file:///Volumes/WorkSpace/Project/REMB/algorithms/DEPLOYMENT.md)
- 🏠 **Main README**: [README.md](file:///Volumes/WorkSpace/Project/REMB/algorithms/README.md)
- 🐳 **Backend Dockerfile**: [Dockerfile](file:///Volumes/WorkSpace/Project/REMB/algorithms/backend/Dockerfile)
- 🎨 **Frontend App**: [app.py](file:///Volumes/WorkSpace/Project/REMB/algorithms/frontend/app.py)
- 🔧 **Docker Compose**: [docker-compose.yml](file:///Volumes/WorkSpace/Project/REMB/algorithms/docker-compose.yml)

---

## Support

- **Hugging Face Spaces**: https://huggingface.co/docs/hub/spaces
- **Streamlit Cloud**: https://docs.streamlit.io/streamlit-community-cloud
- **Docker**: https://docs.docker.com/

**Next Step**: Follow the [DEPLOYMENT.md](file:///Volumes/WorkSpace/Project/REMB/algorithms/DEPLOYMENT.md) guide!
