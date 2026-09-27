SHELL := /bin/bash
RUN := bash scripts/run.sh
UV := $(RUN) uv

.PHONY: install configure db-up db-stop migrate check integration doctor dev-api dev-web
install:
	$(UV) sync --frozen
	$(RUN) npm --prefix frontend ci
configure:
	$(UV) run --frozen python scripts/configure_local.py
db-up:
	$(RUN) docker compose up -d --wait db
db-stop:
	$(RUN) docker compose stop db
migrate:
	$(UV) run --frozen alembic upgrade head
check:
	$(UV) run --frozen ruff check backend scripts
	$(UV) run --frozen ruff format --check backend scripts
	$(UV) run --frozen pytest -m 'not integration'
	$(RUN) npm --prefix frontend run format:check
	$(RUN) npm --prefix frontend run build
integration:
	THERMOSCOPE_RUN_DB_TESTS=1 $(UV) run --frozen pytest -m integration
doctor:
	$(UV) --version
	$(UV) run --frozen python --version
	$(RUN) node --version
	$(RUN) npm --version
	$(RUN) docker version --format '{{.Server.Version}}'
	$(UV) run --frozen python scripts/doctor.py
dev-api:
	$(UV) run --frozen uvicorn thermoscope.main:app --app-dir backend --host 127.0.0.1 --port 8000
dev-web:
	$(RUN) npm --prefix frontend run dev -- --host 127.0.0.1

.PHONY: ingest
ingest:
	PYTHONPATH=backend $(UV) run --frozen python -m thermoscope.ingest $(ARGS)

.PHONY: context
context:
	PYTHONPATH=backend $(UV) run --frozen python -m thermoscope.context_cli $(ARGS)

.PHONY: install-ml ml
install-ml:
	$(UV) sync --frozen --group ml
ml:
	PYTHONPATH=backend $(UV) run --frozen python -m thermoscope.ml_cli $(ARGS)
