.PHONY: help build up down clean logs test docs seed run-dbt test-dbt ml-predict ge-check

help: ## Show this help message
	@echo "Content Intelligence Platform - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build all Docker containers
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

clean: ## Stop services and remove volumes
	docker-compose down -v
	docker system prune -f

logs: ## Show logs from all services
	docker-compose logs -f

logs-fastapi: ## Show FastAPI logs
	docker-compose logs -f fastapi

logs-dbt: ## Show dbt logs
	docker-compose logs -f dbt

logs-postgres: ## Show PostgreSQL logs
	docker-compose logs -f postgres

test: ## Run all tests
	@echo "Running FastAPI tests..."
	docker-compose exec fastapi python -m pytest app/tests/ -v
	@echo "Running dbt tests..."
	docker-compose exec dbt dbt test
	@echo "Running Great Expectations checks..."
	docker-compose exec dbt python -m great_expectations checkpoint run

docs: ## Generate dbt documentation
	docker-compose exec dbt dbt docs generate
	@echo "dbt docs generated at http://localhost:8080"

seed: ## Load seed data
	docker-compose exec dbt dbt seed

run-dbt: ## Run dbt models
	docker-compose exec dbt dbt run

test-dbt: ## Run dbt tests only
	docker-compose exec dbt dbt test

run-dbt-fresh: ## Run dbt with fresh start
	docker-compose exec dbt dbt run --full-refresh

ml-predict: ## Run ML predictions
	docker-compose exec dbt python scripts/ml_predict.py

ge-check: ## Run Great Expectations data quality checks
	docker-compose exec dbt python -m great_expectations checkpoint run

init-db: ## Initialize database schema
	docker-compose exec postgres psql -U content_user -d content_intelligence -f /docker-entrypoint-initdb.d/01_schema.sql

backup: ## Backup database
	docker-compose exec postgres pg_dump -U content_user content_intelligence > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore: ## Restore database (usage: make restore FILE=backup_file.sql)
	docker-compose exec -T postgres psql -U content_user -d content_intelligence < $(FILE)

monitoring: ## Start monitoring services
	docker-compose up -d prometheus grafana
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:3000 (admin/admin123)"

status: ## Show service status
	docker-compose ps

health: ## Check service health
	@echo "Checking FastAPI health..."
	@curl -f http://localhost:8000/healthz || echo "FastAPI not healthy"
	@echo "Checking PostgreSQL health..."
	@docker-compose exec postgres pg_isready -U content_user -d content_intelligence || echo "PostgreSQL not healthy"

dev-setup: ## Setup development environment
	@echo "Setting up development environment..."
	pip install -r requirements.txt
	pip install -r requirements-dbt.txt
	@echo "Installing pre-commit hooks..."
	pre-commit install

lint: ## Run linting and formatting
	@echo "Running black..."
	black app/ dbt/ scripts/
	@echo "Running isort..."
	isort app/ dbt/ scripts/
	@echo "Running flake8..."
	flake8 app/ dbt/ scripts/

format: ## Format code
	black app/ dbt/ scripts/
	isort app/ dbt/ scripts/

security-check: ## Run security checks
	@echo "Running bandit security checks..."
	bandit -r app/ dbt/ scripts/
	@echo "Running safety checks..."
	safety check

full-test: ## Run comprehensive test suite
	@echo "Running linting..."
	$(MAKE) lint
	@echo "Running security checks..."
	$(MAKE) security-check
	@echo "Running unit tests..."
	$(MAKE) test
	@echo "Running data quality checks..."
	$(MAKE) ge-check
	@echo "All tests completed!"

deploy: ## Deploy to production (placeholder)
	@echo "Production deployment not configured"
	@echo "Please configure your deployment pipeline"

# Development shortcuts
dev: up seed run-dbt docs ## Start development environment
	@echo "Development environment ready!"
	@echo "FastAPI: http://localhost:8000"
	@echo "dbt Docs: http://localhost:8080"
	@echo "PostgreSQL: localhost:5432"

quick-test: seed run-dbt test-dbt ## Quick test cycle
	@echo "Quick test cycle completed!" 