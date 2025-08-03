.PHONY: help install dev test lint format clean run docker-build docker-up docker-down

# Default target
help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make dev        - Run development server"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linting"
	@echo "  make format     - Format code"
	@echo "  make clean      - Clean cache files"
	@echo "  make docker-build - Build Docker images"
	@echo "  make docker-up  - Start Docker services"
	@echo "  make docker-down - Stop Docker services"

# Install dependencies
install:
	uv venv
	. .venv/Scripts/activate && uv pip install -r requirements.txt

# Run development server
dev:
	. .venv/Scripts/activate && uvicorn src.api.server:app --reload --host 0.0.0.0 --port 8000

# Run tests
test:
	. .venv/Scripts/activate && pytest -v --cov=src --cov-report=html --cov-report=term

# Run specific test file
test-file:
	. .venv/Scripts/activate && pytest -v $(FILE)

# Run linting
lint:
	. .venv/Scripts/activate && ruff check src tests
	. .venv/Scripts/activate && mypy src

# Format code
format:
	. .venv/Scripts/activate && black src tests
	. .venv/Scripts/activate && isort src tests
	. .venv/Scripts/activate && ruff check --fix src tests

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +

# Docker commands
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Database migrations
db-upgrade:
	. .venv/Scripts/activate && alembic upgrade head

db-downgrade:
	. .venv/Scripts/activate && alembic downgrade -1

db-migration:
	. .venv/Scripts/activate && alembic revision --autogenerate -m "$(MSG)"

# Scraper commands
scrape-reddit:
	. .venv/Scripts/activate && python -m src.scrapers.run reddit --limit 100

scrape-all:
	. .venv/Scripts/activate && python -m src.scrapers.run all --limit 100

# Create example .env file
env-example:
	cp .env.example .env
	@echo "Created .env file. Please update with your credentials."