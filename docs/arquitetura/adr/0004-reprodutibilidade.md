# ADR 0004 - Reprodutibilidade: Docker Compose como ambiente canônico

- **Status:** aceita
- **Data:** 2026-11-02

## Contexto

O examinador precisa reproduzir com fidelidade o que roda localmente, sem depender de versões instaladas na própria máquina.

## Decisão

- **Docker Compose** é o ambiente canônico (serviços `api` e `db`); Python e Postgres só existem dentro dos contêineres.
- **Versões travadas:** imagens com tag de versão exata (`python:3.14.10-slim`, `postgres:17.11-alpine`) e dependências em `requirements.lock` / `requirements-dev.lock` (geradas por pip-tools dentro de um contêiner, `make lock`).
- **Makefile** com alvos padronizados (`make setup`, `up`, `test`, ...).
- **.env gerado localmente** por `make setup`, a partir do `.env.example`.
- **CI** (GitHub Actions) repete lint, tipos, testes, integração com Postgres e build da imagem.

## Alternativas consideradas

- Instalação local com venv e Postgres do sistema: sujeita a diferenças de versão.
- Dev containers: acoplam a solução a uma IDE.
- Lockfile com hashes (`--generate-hashes`): mais estrito, mas adiciona atrito; pode ser adotado depois.

## Consequências

- (+) Mesmo comportamento na máquina do autor, do examinador e na CI.
- (-) Exige Docker instalado.
- (-) Tags de imagem não são digests: uma tag pode, em tese, ser republicada.

**Autoria da decisão:** **requisito humano**; solução proposta pela IA.
