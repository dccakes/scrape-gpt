.PHONY: help setup install clean test test-integration test-all test-coverage lint lint-fix format run shell demo

# Default target
help:
	@echo "LLM Web Scraper v2.0 - Makefile Commands"
	@echo ""
	@echo "Environment Setup:"
	@echo "  make setup            - Full setup: install deps + pre-commit hooks"
	@echo "  make install          - Install project dependencies only"
	@echo "  make clean            - Clean virtual environment and caches"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test             - Run unit tests (fast, isolated)"
	@echo "  make test-integration - Run integration tests (slower)"
	@echo "  make test-all         - Run all tests"
	@echo "  make test-coverage    - Run tests with coverage report"
	@echo "  make lint             - Run ruff and mypy checks"
	@echo "  make lint-fix         - Auto-fix linting issues"
	@echo "  make format           - Format code with black"
	@echo ""
	@echo "Development:"
	@echo "  make run              - Run the scraper CLI"
	@echo "  make demo             - Run the demo (offline, no API key needed)"
	@echo "  make demo-live        - Run the demo against live websites"
	@echo "  make shell            - Start IPython shell with imports"
	@echo ""

# Environment Setup
setup: install pre-commit
	@echo "✅ Setup complete! Run 'source .venv/bin/activate' to activate venv"

install:
	@echo "📦 Installing dependencies..."
	uv pip install -e ".[dev]"
	@echo "✅ Dependencies installed"

clean:
	@echo "🧹 Cleaning up..."
	rm -rf .venv
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	rm -rf **/__pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup complete"

pre-commit:
	@echo "🔧 Setting up pre-commit hooks..."
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit install; \
		echo "✅ Pre-commit hooks installed"; \
	else \
		echo "⚠️  pre-commit not found, skipping hook installation"; \
		echo "    Install with: pip install pre-commit"; \
	fi

# Testing & Code Quality
test:
	@echo "🧪 Running unit tests..."
	python -m pytest tests/unit/ -v -m "unit or not integration and not e2e"

test-integration:
	@echo "🧪 Running integration tests..."
	python -m pytest tests/integration/ -v -m integration

test-all:
	@echo "🧪 Running all tests..."
	python -m pytest tests/ -v

test-coverage:
	@echo "🧪 Running tests with coverage..."
	python -m pytest tests/ --cov=scraper --cov-report=html --cov-report=term-missing
	@echo "📊 Coverage report generated in htmlcov/index.html"

lint:
	@echo "🔍 Running linters..."
	@echo "  → Ruff..."
	ruff check scraper/ tests/
	@echo "  → Mypy..."
	mypy scraper/ --ignore-missing-imports

lint-fix:
	@echo "🔧 Auto-fixing linting issues..."
	ruff check --fix scraper/ tests/
	@echo "✅ Linting fixes applied"

format:
	@echo "✨ Formatting code with black..."
	black scraper/ tests/
	@echo "✅ Code formatted"

# Development
run:
	@echo "🚀 Running scraper CLI..."
	python -m scraper.cli

shell:
	@echo "🐚 Starting IPython shell..."
	@echo "   Available imports:"
	@echo "   - from scraper.domain.models import *"
	@echo "   - from scraper.config import container"
	ipython

demo:
	@echo "🎬 Running demo..."
	python demo/run_demo.py

demo-live:
	@echo "🎬 Running live demo..."
	python demo/run_demo.py --live

# Quick shortcuts
t: test
ti: test-integration
ta: test-all
tc: test-coverage
l: lint
lf: lint-fix
f: format
