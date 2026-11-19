.PHONY: install install-frontend test lint security run run-backend run-frontend build clean

install:
	python -m pip install -e ".[dev,research,web]"

install-frontend:
	cd frontend && npm install

test:
	pytest

lint:
	ruff check src scripts tests
	black --check src scripts tests
	mypy src

security:
	bandit -q -r src
	pip-audit --local --skip-editable
	gitleaks git --redact --log-opts=--all

run:
	python main.py

run-backend:
	python -m backend.api

run-frontend:
	cd frontend && npm run dev

build:
	python scripts/build_exe.py

clean:
	rm -rf frontend/node_modules frontend/dist .pytest_cache .ruff_cache .mypy_cache
