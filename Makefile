WD=$(shell pwd)
PYTHONPATH=${WD}:${WD}/src
SHELL := /bin/bash
UV := uv

.PHONY: help
help:
	@awk 'BEGIN {FS = ":.*?## "}; /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: deploy
deploy: lambda-layer tf-apply ## Install packages and deploy AWS services using Terraform

.PHONY: all 
all: tf-validate run-checks tf-apply ## Run all tests and deploy

.PHONY: invoke
invoke: ## Invoke Lambda (args: q=query d=YYYY-MM-DD ref=reference)
	@command $(UV) run src/local_invoke.py $(if $(q), -q $(q)) $(if $(d), -d $(d)) $(if $(ref), -ref $(ref))

.PHONY: tf-destroy
tf-destroy: ## Destroy infrastructure
	terraform -chdir=terraform destroy -auto-approve -input=false

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
security-test: dev-setup ## Run the security tests (pip-audit + bandit)
	$(UV) run --all-groups pip-audit -lv
	$(UV) run bandit -lll src/*.py test/*.py

.PHONY: lint
lint: dev-setup ## Run linter
	$(UV) run ruff check ./src ./test --exit-zero

.PHONY: fix
fix: dev-setup ## Fix lint errors
	$(UV) run ruff check ./src ./test --fix --exit-zero
	$(UV) run ruff format ./src ./test

.PHONY: unit-test
unit-test: dev-setup ## Run the unit tests with coverage
	$(UV) run pytest --cov=src --cov-report=term-missing -vvvrP

.PHONY: run-checks 
run-checks: security-test lint fix unit-test ## Run all checks

.PHONY: lambda-layer ## Deploy external dependencies for AWS Lambda
lambda-layer: requirements
	$(UV) export --frozen --only-group lambda --no-hashes -o requirements.txt
	mkdir -p layer/python
	$(UV) pip install -r requirements.txt --target ./layer/python
	cd layer && zip -r -X ../layer.zip python
	rm -rf layer/
	rm requirements.txt

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
tf-validate: lambda-layer tf-fmt ## Validate Terraform code
	terraform -chdir=terraform validate

.PHONY: tf-plan
tf-plan: lambda-layer tf-init ## Make Terraform plan
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


