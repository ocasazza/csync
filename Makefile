.PHONY: clean test install dev lint

# Default target
all: clean install test

# Install the package
install:
	pip install -e .

# Install development dependencies
dev:
	pip install -e ".[dev]"
	pip install pytest pytest-cov flake8

# Run tests
test:
	pytest tests/

# Run tests with coverage
coverage:
	pytest --cov=csync tests/

# Run linting
lint:
	flake8 csync/ tests/

# Clean up build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov/
	find . -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete
