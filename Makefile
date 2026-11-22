# Raízes do Nordeste - atalhos de desenvolvimento. Tudo roda via Docker Compose (ambiente canônico).
.DEFAULT_GOAL := help
SHELL := /bin/bash

# UID do usuário do host: faz os arquivos gerados no container (migrações, formatação) serem seus.
export HOST_UID := $(shell id -u)

COMPOSE := docker compose
# Executa um comando no container da API sem subir o banco e sem rodar as migrações.
RUN := $(COMPOSE) run --rm --no-deps --entrypoint "" api
# Versões usadas para regenerar os arquivos .lock (rode `make lock` apenas ao mudar dependências).
LOCK_IMAGE := python:3.14.10-slim
PIP_TOOLS_VERSION := 7.6.2
# Imagem do newman (CLI do Postman) usada por `make postman`.
NEWMAN_VERSION := 6.2.1-alpine

# Pipeline analítico (DW): serviço "analytics" do compose (profile opcional, não sobe no `make up`).
DW_RUN := $(COMPOSE) run --rm --no-deps --entrypoint "" analytics
DW_RUN_DB := $(COMPOSE) run --rm --entrypoint "" analytics
DBT := dbt

.PHONY: help setup up down logs ps shell test test-integration test-all lint format typecheck \
	migrate seed postman revision secrets lock clean dw dw-ingest dw-build dw-test dw-docs dw-lock dw-dirs

help: ## Lista os alvos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

setup: ## Cria o .env (senha aleatória) e ativa o hook de pre-commit
	python3 scripts/setup_env.py
	git config core.hooksPath scripts/git-hooks

up: ## Sobe API + banco em segundo plano (build incluso)
	$(COMPOSE) up -d --build

down: ## Para os contêineres (o volume do banco é preservado)
	$(COMPOSE) down

logs: ## Acompanha os logs da API
	$(COMPOSE) logs -f api

ps: ## Mostra o estado dos serviços
	$(COMPOSE) ps

shell: ## Abre um shell no contêiner da API
	$(COMPOSE) run --rm --no-deps --entrypoint bash api

test: ## Testes unitários e de arquitetura (sem banco)
	$(RUN) pytest -m "not integration"

test-integration: ## Testes de integração contra o PostgreSQL do compose
	$(COMPOSE) run --rm --entrypoint "" api pytest -m integration

test-all: test test-integration ## Todos os testes

lint: ## Verifica estilo e erros (ruff check + format --check)
	$(RUN) ruff check .
	$(RUN) ruff format --check .

format: ## Formata o código e aplica correções automáticas
	$(RUN) ruff check --fix .
	$(RUN) ruff format .

typecheck: ## Verificação estática de tipos (mypy)
	$(RUN) mypy

migrate: ## Aplica as migrações (alembic upgrade head)
	$(COMPOSE) run --rm --entrypoint "" api alembic upgrade head

seed: ## Carga inicial de demonstração (idempotente; exige as migrações aplicadas)
	$(COMPOSE) run --rm --entrypoint "" api python scripts/seed.py

postman: ## Roda a coleção Postman com newman em contêiner (exige `make up` e `make seed`)
	@port=$$(grep -E '^API_PORT=' .env | head -n1 | cut -d= -f2); \
	docker run --network host -v "$(CURDIR)/postman":/etc/newman:ro postman/newman:$(NEWMAN_VERSION) \
		run raizes-mvp.postman_collection.json -e local.postman_environment.json \
		--env-var baseUrl=http://localhost:$${port:-8080}

revision: ## Cria migração: make revision m="mensagem"
	@test -n "$(m)" || { echo 'Informe a mensagem: make revision m="mensagem"'; exit 1; }
	$(COMPOSE) run --rm --entrypoint "" api alembic revision -m "$(m)"

secrets: ## Verifica segredos em todos os arquivos do repositório
	python3 scripts/verificar_segredos.py --todos

lock: ## Regenera requirements*.lock dentro de um contêiner
	docker run --rm -u $(HOST_UID) -e HOME=/tmp -e PIP_NO_WARN_SCRIPT_LOCATION=1 -v "$(CURDIR)":/work -w /work $(LOCK_IMAGE) sh -c '\
		python -m pip install --quiet --user pip-tools==$(PIP_TOOLS_VERSION) && \
		python -m piptools compile --quiet --strip-extras --no-emit-index-url \
			-o requirements.lock pyproject.toml && \
		python -m piptools compile --quiet --strip-extras --no-emit-index-url --extra dev \
			-o requirements-dev.lock pyproject.toml'

# --- Data Warehouse (DuckDB + Parquet + dbt) -------------------------------------------------

dw-dirs:
	@mkdir -p data/lake data/warehouse

dw-ingest: dw-dirs ## DW: extrai eventos novos da outbox para o bronze (Parquet)
	$(DW_RUN_DB) python -m ingestao.extrair_outbox

dw-build: dw-dirs ## DW: dbt seed + build (silver e gold, com testes)
	$(DW_RUN) python -m ingestao.extrair_outbox --somente-esquema
	$(DW_RUN) $(DBT) seed
	$(DW_RUN) $(DBT) build

dw-test: dw-dirs ## DW: testes Python do pipeline + testes de dados do dbt
	$(DW_RUN) pytest -p no:cacheprovider analytics/tests
	$(DW_RUN) python -m ingestao.extrair_outbox --somente-esquema
	$(DW_RUN) $(DBT) seed
	$(DW_RUN) $(DBT) run
	$(DW_RUN) $(DBT) test

dw-docs: dw-dirs ## DW: gera a documentação do dbt (analytics/dbt/raizes_dw/target)
	$(DW_RUN) python -m ingestao.extrair_outbox --somente-esquema
	$(DW_RUN) $(DBT) seed
	$(DW_RUN) $(DBT) docs generate

dw: dw-ingest dw-build ## DW: pipeline completo (ingestão + build)

dw-lock: ## Regenera analytics/requirements.lock dentro de um contêiner
	docker run --rm -u $(HOST_UID) -e HOME=/tmp -e PIP_NO_WARN_SCRIPT_LOCATION=1 -v "$(CURDIR)":/work -w /work $(LOCK_IMAGE) sh -c '\
		python -m pip install --quiet --user pip-tools==$(PIP_TOOLS_VERSION) && \
		python -m piptools compile --quiet --strip-extras --no-emit-index-url \
			-o analytics/requirements.lock analytics/requirements.in'

clean: ## Remove contêineres E o volume do banco (apaga os dados locais!)
	@echo "ATENÇÃO: isto apaga o volume do banco de dados local."
	@read -r -p "Continuar? [s/N] " r && [ "$$r" = "s" ] || { echo "Cancelado."; exit 1; }
	$(COMPOSE) down -v
