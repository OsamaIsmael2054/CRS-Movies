.DEFAULT_GOAL := help

VENV    := .venv
PY      := $(VENV)/bin/python
PIP     := $(VENV)/bin/pip
UVICORN := $(VENV)/bin/uvicorn
COMPOSE := docker compose -f docker/docker-compose.yml
LINE    := 88

.PHONY: help install env format lint db-up db-down db-wait load cf data \
        run run-docker eval eval-cf test clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Create the venv (Python 3.13) and install dependencies
	python3.13 -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt

env: ## Create local env files from templates (if missing)
	@cp -n docker/env/.env.postgres.example docker/env/.env.postgres || true
	@cp -n docker/env/.env.app.example docker/env/.env.app || true

format: ## Auto-format code (isort + black)
	$(PY) -m isort src
	$(PY) -m black --line-length $(LINE) src

lint: ## Check style (pycodestyle, black-compatible)
	$(PY) -m pycodestyle --max-line-length=$(LINE) --ignore=E203,W503 src

db-up: env ## Start PostgreSQL (docker)
	$(COMPOSE) up -d

db-down: ## Stop PostgreSQL
	$(COMPOSE) down

db-wait: ## Wait until PostgreSQL is healthy
	@echo "Waiting for Postgres to become healthy..."
	@until [ "$$(docker inspect -f '{{.State.Health.Status}}' movies_crs_postgres 2>/dev/null)" = "healthy" ]; do sleep 1; done
	@echo "Postgres is healthy."

load: ## Load the dataset into PostgreSQL
	$(PY) -m stores.load

cf: ## Build item-item CF similarity
	$(PY) -m stores.cf_build

data: db-up db-wait load cf ## Full DB setup: start DB, load dataset, build CF

run: ## Start the API locally (uvicorn, reload)
	$(UVICORN) main:app --reload --port 8000

run-docker: env ## Start the full stack (DB + API) in docker
	$(COMPOSE) --profile app up -d --build

eval: ## Run the full evaluation table (sample=50)
	$(PY) -m evaluation.evaluate --methods all --sample 50 --k 10

eval-cf: ## Fast CF-only baseline (sample=500)
	$(PY) -m evaluation.evaluate --methods cf --sample 500 --k 10

test: ## Run the test suite
	$(PY) -m pytest -q

clean: ## Remove Python caches
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
