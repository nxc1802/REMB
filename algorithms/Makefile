.PHONY: help build up down logs clean test-backend test-frontend restart

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker images
	@echo "Building backend Docker image..."
	docker-compose build backend
	@echo "✅ Build complete!"

up: ## Start all services
	@echo "Starting services..."
	docker-compose up -d
	@echo "✅ Services started!"
	@echo "Backend API: http://localhost:8000"
	@echo "Frontend UI: http://localhost:8501"
	@echo "API Docs: http://localhost:8000/docs"

down: ## Stop all services
	@echo "Stopping services..."
	docker-compose down
	@echo "✅ Services stopped!"

logs: ## View logs from all services
	docker-compose logs -f

logs-backend: ## View backend logs only
	docker-compose logs -f backend

logs-frontend: ## View frontend logs only
	docker-compose logs -f frontend

restart: ## Restart all services
	@echo "Restarting services..."
	docker-compose restart
	@echo "✅ Services restarted!"

clean: ## Stop services and remove volumes
	@echo "Cleaning up..."
	docker-compose down -v
	@echo "✅ Cleanup complete!"

test-backend: ## Test backend container
	@echo "Testing backend..."
	@docker build -t land-redistribution-test ./backend
	@docker run --rm -p 7860:7860 -d --name backend-test land-redistribution-test
	@sleep 5
	@echo "Testing health endpoint..."
	@curl -f http://localhost:7860/health || (docker stop backend-test && exit 1)
	@echo "\n✅ Backend test passed!"
	@docker stop backend-test

dev-backend: ## Run backend in development mode (without Docker)
	@echo "Starting backend in development mode..."
	cd backend && uvicorn main:app --reload --port 8000

dev-frontend: ## Run frontend in development mode (without Docker)
	@echo "Starting frontend in development mode..."
	cd frontend && streamlit run app.py --server.port 8501

install-backend: ## Install backend dependencies
	cd backend && pip install -r requirements.txt

install-frontend: ## Install frontend dependencies
	cd frontend && pip install -r requirements.txt

install: install-backend install-frontend ## Install all dependencies

status: ## Show status of services
	docker-compose ps

health: ## Check health of running services
	@echo "Checking backend health..."
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ Backend not responding"
	@echo "\nChecking frontend..."
	@curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:8501 || echo "❌ Frontend not responding"
