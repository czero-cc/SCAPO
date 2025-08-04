.PHONY: help install test lint format clean scrape

# Default target
help:
	@echo "SOTA Practices Commands:"
	@echo ""
	@echo "Setup:"
	@echo "  make install      - Install dependencies with uv"
	@echo ""
	@echo "Development:"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linting" 
	@echo "  make format       - Format code"
	@echo "  make clean        - Clean cache files"
	@echo ""
	@echo "Scraping:"
	@echo "  make scrape       - Run intelligent scraper"

# Install dependencies
install:
	uv venv
	uv pip install -r requirements.txt
	uv run playwright install

# Run tests
test:
	uv run pytest -v

# Run linting
lint:
	uv run ruff check src tests

# Format code
format:
	uv run black src tests
	uv run isort src tests

# Clean cache files  
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

# Run intelligent scraper
scrape:
	uv run python -m src.cli scrape run