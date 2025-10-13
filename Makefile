# Makefile for PianoLED-CoPilot development

.PHONY: help install install-dev test test-cov test-integration lint format clean docs

# Default target
help:
	@echo "Available commands:"
	@echo "  install         Install production dependencies"
	@echo "  install-dev     Install development dependencies"
	@echo "  test            Run all tests"
	@echo "  test-cov        Run tests with coverage"
	@echo "  test-integration Run integration tests"
	@echo "  lint            Run linting checks"
	@echo "  format          Format code with black and isort"
	@echo "  clean           Clean up cache files"
	@echo "  docs            Build documentation"

# Installation
install:
	cd backend && pip install -r requirements.txt

install-dev:
	cd backend && pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install

# Testing
test:
	cd backend && python -m pytest tests/ -v

test-cov:
	cd backend && python -m pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html

test-integration:
	cd backend && python -m pytest tests/test_integration*.py -v

test-led:
	cd backend && python -m pytest tests/test_led_controller.py -v

# Code quality
lint:
	cd backend && flake8 . --max-line-length=127 --extend-ignore=E203,W503
	cd backend && mypy . --ignore-missing-imports --no-strict-optional

format:
	cd backend && black .
	cd backend && isort --profile black .

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +

# Documentation
docs:
	cd docs && sphinx-build -b html . _build/html

# Development server
dev:
	cd backend && python -m flask run --debug

# Pre-commit
pre-commit:
	pre-commit run --all-files

# CI simulation
ci: lint test-cov

# Docker
docker-build:
	docker build -t pianoled-copilot .

docker-run:
	docker run -p 5000:5000 pianoled-copilot