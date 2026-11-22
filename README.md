# Raízes do Nordeste - API back-end

Projeto acadêmico (Projeto Multidisciplinar, trilha Back-end): API para a rede de lanchonetes
"Raízes do Nordeste", com pedidos multicanal (app, totem, balcão, pick-up e web), unidades com
cardápios e estoques distintos, programa de fidelidade com conformidade à LGPD, pagamento por
gateway externo, relatórios para a matriz e alta disponibilidade em horário de pico.

**Stack:** Python 3.14, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 17, Docker Compose.
**Analítico:** Data Warehouse com margem para Lakehouse (DuckDB, Parquet, dbt-core, Kimball).
**Arquitetura:** aplicação única em 4 camadas (API, Aplicação, Domínio, Infraestrutura).

> **Estado atual:** requisitos e modelagem concluídos (casos de uso, DER, classes, sequência e
> estados). A implementação cobre só a fatia mínima exigida pelo roteiro (fluxo A: login, pedido,
> pagamento mock, status, auditoria, consentimento e outbox), por decisão do autor (D-057): o
> diferencial do trabalho é a análise construir × comprar.

## Para o avaliador: roteiro de leitura

| Critério do roteiro | Onde ver |
|---|---|
| Análise e requisitos | [docs/requisitos/](docs/requisitos/README.md) |
| Modelagem e arquitetura | [docs/modelagem/](docs/modelagem/README.md) e [docs/arquitetura/](docs/arquitetura/visao-geral.md) |
| API e endpoints | [docs/api/](docs/api/README.md) e o Swagger em `/docs` com a API rodando |
| LGPD e segurança | [docs/requisitos/ §7](docs/requisitos/README.md#7-lgpd-mínimo-técnico) e [ADR 0005](docs/arquitetura/adr/0005-protecao-de-credenciais-e-dados-pessoais.md) |
| Entrega técnica | este README (seção "Como reproduzir") |
| Plano de testes | [docs/testes/](docs/testes/README.md) |
| Documento principal (fonte do PDF) | [docs/entrega/documento-principal.md](docs/entrega/documento-principal.md) |
| Uso de IA (ferramenta, prompts, trechos) | [docs/uso-de-ia/](docs/uso-de-ia/README.md) |

As referências ao enunciado aparecem como **RT p. N** (Roteiro de Atividade Prática da Trilha
Back-end, 2026) e **RG p. N** (Roteiro geral com o estudo de caso), sempre pela página do PDF
oficial distribuído na disciplina. Os roteiros não são redistribuídos neste repositório.

## Como reproduzir

O Docker é o ambiente canônico: o que roda no seu computador é o mesmo que roda na CI.

**Pré-requisitos:** Docker Engine com Docker Compose v2, `make`, `git` e `python3` (apenas para
os scripts auxiliares `setup` e `secrets`, que usam só a biblioteca padrão).

```bash
git clone <URL deste repositório no GitHub>
cd raizes-do-nordeste-backend

make setup   # cria o .env (senha aleatória do banco) e ativa o hook de pre-commit
make up      # constrói a imagem, sobe banco + API e aplica as migrações
```

Depois de `make up`:

| Recurso            | URL                                        |
|--------------------|--------------------------------------------|
| Swagger (OpenAPI)  | `http://localhost:${API_PORT}/docs`        |
| OpenAPI JSON       | `http://localhost:${API_PORT}/openapi.json`|
| Liveness           | `http://localhost:${API_PORT}/health/live` |
| Readiness (banco)  | `http://localhost:${API_PORT}/health/ready`|

`API_PORT` vem do `.env` (padrão do modelo: `8080`). Se a porta estiver ocupada na sua máquina,
edite `API_PORT` / `DB_HOST_PORT` no `.env` e rode `make up` novamente.

```bash
make test              # testes unitários + arquitetura (sem banco)
make test-integration  # testes contra o PostgreSQL real do compose
make lint              # ruff (check + format --check)
make typecheck         # mypy
make secrets           # verificação de segredos em todo o repositório
make down              # para os contêineres (mantém os dados)
make help              # lista todos os alvos
```

Observações:

- O `.env` é gerado localmente e **nunca é versionado**. Se apagá-lo, gere outro com `make setup`
  e rode `make clean` (apaga o volume do banco, pois a senha antiga ficou gravada nele).
- Versões travadas: imagens (`python:3.14.10-slim`, `postgres:17.11-alpine`) e dependências
  (`requirements.lock`, `requirements-dev.lock`, `analytics/requirements.lock`). Para atualizar dependências: edite o
  `pyproject.toml` e rode `make lock`.
- Migrações: aplicadas automaticamente ao iniciar o contêiner da API; manualmente com
  `make migrate`; nova migração com `make revision m="descrição"`.

## Data Warehouse

Camada analítica opcional (DuckDB + Parquet + dbt), alimentada pela outbox de eventos de domínio.
Não sobe no `make up`; rode depois dele:

```bash
make dw           # extrai eventos da outbox para o bronze e roda dbt (silver + gold + testes)
make dw-ingest    # só a ingestão          make dw-build   # só o dbt (seed + build)
make dw-test      # testes do pipeline     make dw-docs    # docs do dbt
```

Os arquivos gerados ficam em `data/` (fora do git). Sem eventos na outbox o pipeline também
funciona (bronze vazio). Detalhes: [analytics/README.md](analytics/README.md) e
[docs/dados/](docs/dados/README.md).

## Estrutura de pastas

```
src/raizes/
  api/             # camada API: HTTP (routers, schemas, dependências, erros, middleware)
  application/     # camada Aplicação: casos de uso e portas (Protocols)
  domain/          # camada Domínio: regras de negócio, sem frameworks
  infrastructure/  # camada Infraestrutura: config, logs, banco (implementa as portas)
  main.py          # create_app(): composição da aplicação
migrations/        # migrações Alembic
contracts/         # contratos de dados (esquemas JSON e contratos no estilo ODCS)
analytics/         # pipeline do Data Warehouse (ingestão, dbt, testes)
tests/             # unit/, architecture/ (regra de camadas), integration/
data/              # (gerado, fora do git) lake Parquet e warehouse DuckDB
scripts/           # setup_env.py, verificar_segredos.py, git-hooks/
docs/              # documentação do projeto
.github/workflows/ # CI
```

## Documentação

- [Visão geral da arquitetura](docs/arquitetura/visao-geral.md)
- [Decisões de arquitetura (ADRs)](docs/arquitetura/adr/)
- [Requisitos](docs/requisitos/README.md)
- [Modelagem](docs/modelagem/README.md)
- [Arquitetura de dados (DW)](docs/dados/README.md) e [matriz de barramento](docs/dados/matriz-de-barramento.md)
- [Dicionário de dados](docs/dados/dicionario-de-dados.md) e [contratos de dados](contracts/README.md)
- [Testes](docs/testes/README.md)
- [API](docs/api/README.md)

## Segurança e dados pessoais

Nenhuma credencial é versionada: o `.env` é ignorado pelo git, o `.env.example` contém apenas
valores fictícios, e um verificador de segredos roda no pre-commit e na CI
(ver [ADR 0005](docs/arquitetura/adr/0005-protecao-de-credenciais-e-dados-pessoais.md)).

## Uso de IA

Este projeto foi desenvolvido com apoio de IA, e o uso é registrado de forma transparente
(conversas e decisões humano × IA). Veja [docs/uso-de-ia/README.md](docs/uso-de-ia/README.md).
