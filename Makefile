# Define utility variable for uv-related functionality
WD=$(shell pwd)
PYTHONPATH=${WD}:${WD}/src
SHELL := /bin/bash
UV := uv

## Run all commands.
.PHONY: all
all: uv dev-setup requirements run-checks

.PHONY: uv
uv:  ## Install uv if it's not present.
	@command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh

.PHONY: dev-setup
dev-setup: ## Install dev packages
	$(UV) sync --dev

# Build the environment requirements
.PHONY: requirements
requirements: uv
	$(UV) sync --frozen

## Run the security test (bandit + pip-audit)
.PHONY: security-test
security-test:
	$(UV) run --all-groups pip-audit -lv
	$(UV) run bandit -lll src/*.py test/*.py

.PHONY: lint
lint:  ## Run linter
	$(UV) run ruff check ./src ./test

.PHONY: fix
fix:  ## Fix lint errors
	$(UV) run ruff check ./src ./test --fix
	$(UV) run ruff format ./src ./test

## Run the unit tests with coverage
.PHONY: unit-test
unit-test:
	$(UV) run pytest --cov=src --cov-report=term-missing -vvvrP

## Run all checks
.PHONY: run-checks
run-checks: security-test lint fix unit-test
