# Deployment Guide

Complete guide for deploying the Land Redistribution Algorithm to production.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Backend Deployment (Hugging Face Spaces)](#backend-deployment-hugging-face-spaces)
- [Frontend Deployment (Streamlit Cloud)](#frontend-deployment-streamlit-cloud)
- [Local Docker Testing](#local-docker-testing)
- [Environment Variables](#environment-variables)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### For All Deployments
- Git installed on your machine
- GitHub account (for Streamlit Cloud)
- Hugging Face account (for backend deployment)

### For Local Testing
- Docker and Docker Compose installed
- Python 3.11+ (for non-Docker development)
- Make (optional, for convenience commands)

## Backend Deployment (Hugging Face Spaces)

Hugging Face Spaces provides free hosting for ML applications with Docker support.

### Step 1: Create a New Space

1. Go to [Hugging Face Spaces](https://huggingface.co/spaces)
2. Click **"Create new Space"**
3. Configure:
   - **Space name**: `land-redistribution-api` (or your choice)
   - **License**: MIT
   - **Select the Space SDK**: Docker
   - **Visibility**: Public or Private

### Step 2: Prepare Backend Files

The backend directory is already configured with:
- ✅ `Dockerfile` - Multi-stage production build
- ✅ `README_HF.md` - Hugging Face metadata
- ✅ `requirements.txt` - Python dependencies
- ✅ `.dockerignore` - Build optimization

### Step 3: Deploy to Hugging Face

#### Option A: Git Push (Recommended)

```bash
# Navigate to backend directory
cd /Volumes/WorkSpace/Project/REMB/algorithms/backend

# Initialize git (if not already)
git init

# Add Hugging Face remote using your space name
git remote add hf https://huggingface.co/spaces/<YOUR_USERNAME>/<SPACE_NAME>

# Rename README for Hugging Face
cp README_HF.md README.md

# Add and commit files
git add .
git commit -m "Initial deployment"

# Push to Hugging Face
git push hf main
```

#### Option B: Web Upload

1. In your Space, click **"Files and versions"**
2. Upload all files from `backend/` directory
3. Ensure `README_HF.md` is renamed to `README.md`

### Step 4: Wait for Build

- Hugging Face will automatically build your Docker image
- Build time: ~5-10 minutes
- Monitor progress in the "Logs" tab

### Step 5: Test Your Backend API

Once deployed, your API will be available at:
```
https://<YOUR_USERNAME>-<SPACE_NAME>.hf.space
```

Test endpoints:
```bash
# Health check
curl https://<YOUR_USERNAME>-<SPACE_NAME>.hf.space/health

# API documentation
open https://<YOUR_USERNAME>-<SPACE_NAME>.hf.space/docs
```

## Frontend Deployment (Streamlit Cloud)

### Step 1: Push Frontend to GitHub

```bash
cd /Volumes/WorkSpace/Project/REMB/algorithms/frontend

# Initialize git repository (if not already)
git init

# Add GitHub remote
git remote add origin https://github.com/<YOUR_USERNAME>/land-redistribution-ui.git

# Add all files
git add .
git commit -m "Initial commit"

# Push to GitHub
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Streamlit Cloud

1. Go to [Streamlit Cloud](https://streamlit.io/cloud)
2. Sign in with GitHub
3. Click **"New app"**
4. Configure:
   - **Repository**: Select your frontend repository
   - **Branch**: `main`
   - **Main file path**: `app.py`

### Step 3: Configure Environment Variables

In Streamlit Cloud, add secrets:

1. Go to your app settings
2. Click **"Secrets"**
3. Add:
```toml
API_URL = "https://<YOUR_HF_USERNAME>-<SPACE_NAME>.hf.space"
```

### Step 4: Deploy

- Click **"Deploy"**
- Streamlit Cloud will install dependencies and launch your app
- Your app will be available at: `https://<APP_NAME>.streamlit.app`

## Local Docker Testing

Before deploying to production, test locally with Docker Compose.

### Quick Start

```bash
# Navigate to algorithms directory
cd /Volumes/WorkSpace/Project/REMB/algorithms

# Build and start services
make build
make up

# View logs
make logs

# Test services
make health
```

### Manual Testing

```bash
# Build backend
docker-compose build backend

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Test backend
curl http://localhost:8000/health

# Access frontend
open http://localhost:8501

# Stop services
docker-compose down
```

### Testing the Backend Container Only

```bash
cd backend

# Build image
docker build -t land-redistribution-api .

# Run container
docker run -p 7860:7860 land-redistribution-api

# Test in another terminal
curl http://localhost:7860/health
```

## Environment Variables

### Backend (.env or Hugging Face Secrets)

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

# Production (use your actual Hugging Face Space URL)
API_URL=https://<YOUR_HF_USERNAME>-<SPACE_NAME>.hf.space
```

## Troubleshooting

### Backend Issues

#### Build Fails on Hugging Face

**Problem**: Docker build fails with dependency errors

**Solution**:
1. Check Dockerfile syntax
2. Verify requirements.txt has pinned versions
3. Check build logs in Hugging Face Space
4. Test locally first: `docker build -t test ./backend`

#### API Returns 500 Error

**Problem**: Backend starts but API endpoints fail

**Solution**:
1. Check logs in Hugging Face Space
2. Verify all imports work: Test locally with Docker
3. Check CORS settings in `main.py`

#### Slow Performance

**Problem**: API is slow or times out

**Solution**:
- Reduce optimization parameters (population_size, generations)
- Consider upgrading to Hugging Face paid tier for more resources
- Add caching for common requests

### Frontend Issues

#### Cannot Connect to Backend

**Problem**: Frontend shows "Cannot connect to API"

**Solution**:
1. Verify `API_URL` environment variable is set correctly in Streamlit Secrets
2. Check backend is running: Visit backend URL directly
3. Check CORS settings on backend
4. Verify no typos in API_URL (should include https://)

#### Streamlit Cloud Build Fails

**Problem**: Deployment fails on Streamlit Cloud

**Solution**:
1. Check `requirements.txt` for incompatible versions
2. Verify `app.py` has no syntax errors
3. Check Streamlit Cloud build logs
4. Test locally: `streamlit run app.py`

### Docker Compose Issues

#### Port Already in Use

**Problem**: `Error: port is already allocated`

**Solution**:
```bash
# Find process using port
lsof -i :8000
lsof -i :8501

# Kill process
kill -9 <PID>

# Or change ports in docker-compose.yml
```

#### Container Crashes on Startup

**Problem**: Service exits immediately

**Solution**:
```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend

# Run container interactively
docker run -it land-redistribution-api /bin/bash

# Check health
docker-compose ps
```

## Performance Optimization

### Backend

1. **Reduce CPU-intensive operations**:
   - Lower default `population_size` and `generations`
   - Add request timeouts
   - Implement result caching

2. **Optimize Docker image**:
   - Use multi-stage builds (already implemented)
   - Minimize layers
   - Remove unnecessary dependencies

### Frontend

1. **Optimize Streamlit**:
   - Use `@st.cache_data` for expensive computations
   - Lazy load visualizations
   - Reduce re-renders with `st.session_state`

2. **Reduce API calls**:
   - Cache results in session state
   - Batch multiple requests

## Monitoring

### Hugging Face Spaces

- View logs: Space → Logs tab
- Check metrics: Space → Settings → Usage
- Restart: Space → Settings → Factory reboot

### Streamlit Cloud

- View logs: App → Manage app → Logs
- Check analytics: App → Analytics
- Restart: App → Manage app → Reboot app

## Security Considerations

1. **Environment Variables**: Never commit `.env` files with secrets
2. **CORS**: In production, replace `CORS_ORIGINS=*` with specific domains
3. **Rate Limiting**: Consider adding rate limiting for public APIs
4. **Input Validation**: Backend validates all inputs (already implemented)

## Next Steps

1. ✅ Test locally with Docker Compose
2. ✅ Deploy backend to Hugging Face Spaces
3. ✅ Deploy frontend to Streamlit Cloud
4. ✅ Configure environment variables
5. ✅ Test end-to-end flow
6. 📝 Monitor performance and logs
7. 🚀 Share with users!

## Support

For issues or questions:
- Backend API: Check Hugging Face Space discussions
- Frontend: Check Streamlit Community forum
- General: Open an issue on GitHub

## License

MIT
