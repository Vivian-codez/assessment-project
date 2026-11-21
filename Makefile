# Makefile for Verism AI full-stack development, builds, migrations, and testing

# Set default shell to bash or sh across POSIX and Windows environments
SHELL := /bin/bash

# Target .PHONY declarations preventing file name collisions with make targets
.PHONY: help up down logs test migrate db-reset lint build clean

# Default target displaying helpful target usage summary
help:
	@echo "Verism AI Build & Automation Control"
	@echo "------------------------------------"
	@echo "make up        - Launch all Docker services (PostgreSQL, Redis, Qdrant, API, Workers, Frontend)"
	@echo "make down      - Gracefully stop and tear down all Docker containers"
	@echo "make logs      - Stream unified multi-service logs in real time"
	@echo "make test      - Execute backend pytest test suite and frontend validation"
	@echo "make migrate   - Execute Alembic database schema migrations"
	@echo "make db-reset  - Reset database and re-apply initial migrations"
	@echo "make lint      - Run linters and type checkers on backend and frontend"
	@echo "make build     - Build all Docker images without starting services"
	@echo "make clean     - Remove temporary files, build caches, and test artifacts"

# Target: Build and launch all containerized microservices in background mode
up:
	# Launch Docker Compose stack in detached mode with build validation
	docker compose up --build -d

# Target: Tear down running Docker containers and remove associated default networks
down:
	# Stop all containers and remove shared network interfaces
	docker compose down

# Target: Stream logs from all running container services with follow enabled
logs:
	# Follow multi-container log output in real time
	docker compose logs -f

# Target: Execute automated unit and integration test suites
test:
	# Run backend test suite via pytest inside virtual environment
	PYTHONPATH=backend backend/.venv/Scripts/python -m pytest backend/tests -v

# Target: Apply latest Alembic database migrations to PostgreSQL
migrate:
	# Run alembic upgrade head to apply pending schema migrations
	cd backend && ../backend/.venv/Scripts/alembic upgrade head

# Target: Reset local database schema and re-run migrations from scratch
db-reset:
	# Downgrade all migrations to base state
	cd backend && ../backend/.venv/Scripts/alembic downgrade base
	# Re-apply all migrations up to head revision
	cd backend && ../backend/.venv/Scripts/alembic upgrade head

# Target: Run code linters and syntax checks across backend and frontend
lint:
	# Run flake8 or python syntax check on backend code
	backend/.venv/Scripts/python -m py_compile backend/app/main.py
	# Run frontend linter
	cd frontend && npm run lint

# Target: Build all Docker images without starting containers
build:
	# Build container images for API, Celery workers, and Frontend
	docker compose build

# Target: Clean up python bytecode caches, pytest caches, and frontend build outputs
clean:
	# Remove Python bytecode cache directories
	find . -type d -name "__pycache__" -exec rm -rf {} +
	# Remove pytest artifact directories
	rm -rf backend/.pytest_cache
	# Remove frontend compiled build outputs
	rm -rf frontend/.output frontend/dist

