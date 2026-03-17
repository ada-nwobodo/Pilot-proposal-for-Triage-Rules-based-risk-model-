.PHONY: install dev run test test-unit test-integration test-api coverage docker-build docker-up docker-down clean

# ── Local development ──────────────────────────────────────────────────────────

install:
	pip install --upgrade pip
	pip install -r requirements.txt
	python -m spacy download en_core_web_sm
	pip install -e .

dev: install
	uvicorn api.main:app --reload --port 8000

# ── Tests ──────────────────────────────────────────────────────────────────────

test:
	pytest

test-unit:
	pytest tests/unit/

test-integration:
	pytest tests/integration/

test-api:
	pytest tests/api/

coverage:
	coverage run -m pytest
	coverage report -m
	coverage html

# ── Docker ─────────────────────────────────────────────────────────────────────

docker-build:
	docker compose build

docker-up:
	docker compose up --build

docker-down:
	docker compose down

# ── Housekeeping ───────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage dist build *.egg-info
