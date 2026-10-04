.PHONY: help dev dev-be dev-fe test test-be test-fe lint lint-be lint-fe format clean docker-up docker-down

# Default target
help: ## Show this help message
	@echo "WebGuard - Development Commands"
	@echo "================================"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================
# Development
# ============================================

dev: ## Run both backend and frontend in development mode
	@echo "Starting Backend & Frontend..."
	@$(MAKE) dev-be &
	@$(MAKE) dev-fe

dev-be: ## Run backend development server
	cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-fe: ## Run frontend development server
	cd frontend && npm run dev

# ============================================
# Testing
# ============================================

test: test-be test-fe ## Run all tests

test-be: ## Run backend tests
	cd backend && python -m pytest

test-fe: ## Run frontend tests
	cd frontend && npm test

# ============================================
# Linting & Formatting
# ============================================

lint: lint-be lint-fe ## Run all linters

lint-be: ## Lint backend code
	cd backend && python -m ruff check app/ tests/
	cd backend && python -m mypy app/

lint-fe: ## Lint frontend code
	cd frontend && npm run lint

format: ## Format all code
	cd backend && python -m ruff check --fix app/ tests/
	cd backend && python -m black app/ tests/
	cd frontend && npm run format

# ============================================
# Docker
# ============================================

docker-up: ## Start all services with Docker Compose
	cd docker && docker compose up -d

docker-down: ## Stop all Docker services
	cd docker && docker compose down

docker-dev: ## Start development Docker environment
	cd docker && docker compose -f docker-compose.dev.yml up -d

docker-build: ## Build Docker images
	cd docker && docker compose build

# ============================================
# Setup & Maintenance
# ============================================

setup: ## Initial project setup
	@echo "Setting up Backend..."
	cd backend && python -m venv .venv
	cd backend && .venv/Scripts/activate && pip install -e ".[dev]"
	@echo "Setting up Frontend..."
	cd frontend && npm install
	@echo "Setting up pre-commit hooks..."
	pre-commit install
	@echo "Setup complete! Run 'make dev' to start developing."

clean: ## Clean build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/htmlcov backend/.coverage
	@echo "Cleaned!"

audit: ## Run security audit on dependencies
	cd backend && pip-audit
	cd frontend && npm audit
