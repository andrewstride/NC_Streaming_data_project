WD=$(shell pwd)
PYTHONPATH=${WD}:${WD}/src
SHELL := /bin/bash
UV := uv

.PHONY: all 
all: uv dev-setup requirements run-checks ## Run all commands.

.PHONY: uv
uv:  ## Install uv if it's not present.
	@command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh

.PHONY: requirements
requirements: uv ## Build the environment requirements
	$(UV) sync --frozen

.PHONY: dev-setup
dev-setup: requirements ## Install dev packages
	$(UV) sync --dev

.PHONY: security-test
security-test: dev-setup ## Run the security test (pip-audit + bandit)
	$(UV) run --all-groups pip-audit -lv
	$(UV) run bandit -lll src/*.py test/*.py

.PHONY: lint
lint: dev-setup ## Run linter
	$(UV) run ruff check ./src ./test

.PHONY: fix
fix: dev-setup ## Fix lint errors
	$(UV) run ruff check ./src ./test --fix
	$(UV) run ruff format ./src ./test

.PHONY: unit-test
unit-test: dev-setup ## Run the unit tests with coverage
	$(UV) run pytest --cov=src --cov-report=term-missing -vvvrP

.PHONY: run-checks 
run-checks: security-test lint fix unit-test ## Run all checks

.PHONY: tf-check
tf-check: ## Check Terraform installed
		@command -v terraform >/dev/null 2>&1 || echo "Terraform install required: visit https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli"

.PHONY: tf-init
tf-init: tf-check ## Initialise Terraform
	terraform -chdir=terraform init

.PHONY: tf-fmt
tf-fmt: tf-init ## Format Terraform code
	terraform -chdir=terraform fmt

.PHONY: tf-validate
tf-validate: tf-init ## Validate Terraform code
	terraform -chdir=terraform validate

.PHONY: tf-plan
tf-plan: tf-init ## Make Terraform plan
	terraform -chdir=terraform plan -input=false

.PHONY: tf-plan-cicd
tf-plan-cicd: tf-init ## Make Terraform plan with out-file and exit-code
	terraform -chdir=terraform plan -detailed-exitcode -out=tfplan -input=false

.PHONY: tf-apply
tf-apply: tf-plan ## Apply Terraform plan
	terraform -chdir=terraform apply -auto-approve -input=false

.PHONY: tf-apply-cicd
tf-apply-cicd: tf-plan-cicd ## Apply Terraform plan from out-file
	terraform -chdir=terraform apply -auto-approve -input=false tfplan

.PHONY: tf-destroy
tf-destroy: ## Destroy infrastructure
	terraform -chdir=terraform destroy -auto-approve -input=false