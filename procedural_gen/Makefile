.PHONY: help install dev backend frontend build up down clean test

# Default target
help:
	@echo "Procedural Generation - Available Commands"
	@echo "==========================================="
	@echo "make install    - Install all dependencies"
	@echo "make dev        - Start dev servers (backend + frontend)"
	@echo "make backend    - Start backend only"
	@echo "make frontend   - Start frontend only"
	@echo "make build      - Build Docker images"
	@echo "make up         - Start Docker containers"
	@echo "make down       - Stop Docker containers"
	@echo "make test       - Run tests"
	@echo "make clean      - Clean cache files"

# Install dependencies
install:
	cd backend && pip install -r requirements.txt
	cd frontend && pip install -r requirements.txt

# Development servers
dev:
	@echo "Starting backend and frontend..."
	@make backend &
	@sleep 2
	@make frontend

backend:
	cd backend && uvicorn main:app --reload --port 8000

frontend:
	cd frontend && streamlit run app.py

# Docker commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

# Testing
test:
	cd backend && pytest tests/ -v

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
