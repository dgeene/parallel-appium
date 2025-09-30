# Makefile for Parallel Appium Hub

.PHONY: help install install-dev clean test test-parallel start-hub stop-hub lint format check

# Default target
help:
	@echo "Available targets:"
	@echo "  install      - Install the package and dependencies"
	@echo "  install-dev  - Install with development dependencies"
	@echo "  clean        - Clean up build artifacts and logs"
	@echo "  test         - Run tests"
	@echo "  test-parallel - Run tests in parallel (4 workers)"
	@echo "  start-hub    - Start the Appium hub"
	@echo "  stop-hub     - Stop any running hub processes"
	@echo "  lint         - Run linting checks"
	@echo "  format       - Format code with black"
	@echo "  check        - Run all checks (lint, type check, test)"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

# Cleanup
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf logs/*.log
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

# Testing
test:
	pytest tests/ -v

test-parallel:
	pytest tests/ -n 4 -v

test-coverage:
	pytest tests/ --cov=src/appium_hub --cov-report=html

# Hub management
start-hub:
	python start_hub.py

start-hub-dev:
	python start_hub.py --log-level DEBUG

stop-hub:
	pkill -f "appium_hub" || true
	pkill -f "start_hub.py" || true

# Development tools
lint:
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/

check: lint test

# Docker support (optional)
docker-build:
	docker build -t appium-hub .

docker-run:
	docker run -p 4444:4444 -p 4723-4773:4723-4773 appium-hub

# Development environment setup
setup-dev: install-dev
	mkdir -p logs
	cp config.env.example config.env
	@echo "Development environment setup complete!"
	@echo "Edit config.env as needed, then run 'make start-hub'"