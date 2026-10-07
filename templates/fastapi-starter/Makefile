PY ?= python

.PHONY: run test lint migrate revision
run:
	$(PY) -m uvicorn app.main:app --reload
test:
	$(PY) -m pytest -q
lint:
	$(PY) -m ruff check . && $(PY) -m ruff format --check .
migrate:
	$(PY) -m alembic upgrade head
revision:
	$(PY) -m alembic revision --autogenerate -m "$(m)"
