.PHONY: install run test test-api test-e2e clean

PY := ./.venv/bin/python

install:
	python3 -m venv .venv
	$(PY) -m pip install -r requirements-dev.txt

run:
	$(PY) -m uvicorn backend.main:app --port 8000 --reload

test:
	$(PY) -m pytest

test-api:
	$(PY) -m pytest tests/backend

test-e2e:
	$(PY) -m pytest tests/e2e

clean:
	rm -f fooddash.db
	find . -name __pycache__ -not -path "./.venv/*" -prune -exec rm -rf {} +
