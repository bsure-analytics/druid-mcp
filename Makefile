.PHONY: help install format lint check test all clean build docker-build docker-run docker-stop docker-clean

help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies including dev dependencies"
	@echo "  make format        - Format code with ruff"
	@echo "  make lint          - Lint code with ruff"
	@echo "  make check         - Run linting without fixing"
	@echo "  make test          - Run tests with pytest"
	@echo "  make all           - Run format, lint, and test"
	@echo "  make clean         - Remove cache files"
	@echo "  make build         - Build Docker image"
	@echo ""
	@echo "Docker commands:"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-run    - Run Docker container"
	@echo "  make docker-stop   - Stop Docker container"
	@echo "  make docker-clean  - Remove Docker image and container"

install:
	uv sync --extra dev

format:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff check --fix .

check:
	uv run ruff check .
	uv run ruff format --check .

test:
	uv run pytest tests/ -v

all: format lint test

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete


docker-build:
	docker build -t druid-mcp:latest .

docker-run:
	docker compose up

docker-run-build:
	docker compose up --build

docker-stop:
	docker compose down

docker-clean:
	docker compose down -v
	docker rmi druid-mcp:latest