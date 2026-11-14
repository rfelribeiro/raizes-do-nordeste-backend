# analytics/ - pipeline do Data Warehouse

Pipeline analítico da Raízes do Nordeste: outbox (PostgreSQL) -> bronze (Parquet) -> silver e
gold (dbt + DuckDB). Arquitetura, convenções e LGPD: [docs/dados/README.md](../docs/dados/README.md).
Decisões: [ADR 0007](../docs/arquitetura/adr/0007-visao-analitica.md) e [ADR 0008](../docs/arquitetura/adr/0008-plataforma-analitica.md) e [ADR 0009](../docs/arquitetura/adr/0009-nomenclatura-e-contratos-de-dados.md).
Nomes e tipos de cada objeto: [dicionário de dados](../docs/dados/dicionario-de-dados.md); contratos: [contracts/](../contracts/README.md).
O catálogo vivo é o `dbt docs` (`make dw-docs`).
## Como rodar

Pré-requisito: `make setup` e `make up` (o banco precisa estar acessível). O serviço `analytics`
do compose usa um *profile* e **não sobe** no `make up`; é executado sob demanda pelos alvos abaixo.

```bash
make dw          # ingestão + build (caminho completo)
make dw-ingest   # só extrai eventos novos da outbox para o bronze
make dw-build    # dbt seed + build (silver e gold, com testes)
make dw-test     # testes Python do pipeline + testes de dados do dbt
make dw-docs     # dbt docs generate (analytics/dbt/raizes_dw/target)
make dw-lock     # regenera analytics/requirements.lock (só ao mudar requirements.in)
```

Saídas, todas locais e fora do git (`data/`):

```
data/lake/bronze/outbox_events/dt=AAAA-MM-DD/<run_id>.parquet
data/lake/_state/outbox_events.json        # marca d'água da extração
data/warehouse/raizes.duckdb                 # silver (schema silver) e gold (schema gold)
```

Consultar o resultado, por exemplo:

```bash
docker compose run --rm --no-deps --entrypoint "" analytics python -c \
  "import duckdb; print(duckdb.connect('/app/data/warehouse/raizes.duckdb', read_only=True).sql('select count(*) from gold.dim_date'))"
```

## Estrutura

```
ingestion/extract_outbox.py   # extrator incremental (funções puras + I/O)
ingestion/generate_holidays.py # gera o seed de feriados nacionais (algoritmo da Páscoa)
tests/                       # testes das funções puras
dbt/raizes_dw/               # projeto dbt: models/staging (silver), models/marts (gold), seeds
Dockerfile                   # imagem do serviço analytics (Python 3.14.10, usuário não-root)
requirements.in / .lock      # dependências travadas (geradas dentro de contêiner)
```

## Como funciona a extração

1. Lê `last_sequence_id` de `_state/outbox_events.json` (0 se não existir).
2. Seleciona de `outbox_events` as linhas com `sequence_id` maior que a marca d'água e
   `recorded_at` anterior a "agora - atraso" (padrão 5 s, `DW_EXTRACTION_LAG_SECONDS`).
   O atraso de segurança evita pular eventos de transações que confirmam fora de ordem; transações mais longas
   que o atraso de segurança continuam sendo um risco residual (ver ADR 0008).
3. Agrupa por data de captura (UTC) e grava um Parquet por partição (`dt=`), de forma atômica.
4. **Somente depois** de gravar tudo, atualiza a marca d'água (também de forma atômica).

É idempotente: sem eventos novos, nada é gravado. Se falhar antes do passo 4, a próxima execução
relê as mesmas linhas; a silver deduplica por `event_id`, então não há dupla contagem.
A conexão usa as variáveis `POSTGRES_*` já usadas pela API; a senha nunca é logada.

## Bronze vazio

Antes de existir qualquer evento, o glob `bronze/outbox_events/*/*.parquet` não encontraria
arquivo e o dbt falharia. Solução: o extrator (e `--schema-only`, usado por `make dw-build`
e pela CI, sem acessar o banco) cria `dt=1970-01-01/_empty_schema.parquet`, um Parquet com 0 linhas
e o esquema do bronze. Assim `stg_outbox_events` funciona (e retorna 0 linhas) sem eventos.

## Variáveis de ambiente

| Variável | Uso | Padrão |
|---|---|---|
| `DW_DUCKDB_PATH` | arquivo DuckDB | `data/warehouse/raizes.duckdb` (no compose: `/app/data/warehouse/raizes.duckdb`) |
| `DW_LAKE_PATH` | raiz do lake | `data/lake` (no compose: `/app/data/lake`) |
| `DW_EXTRACTION_LAG_SECONDS` | atraso de segurança da extração | `5` |
| `ANALYTICS_PSEUDONYM_KEY` | segredo do HMAC de pseudonimização (gerado por `make setup`) | sem padrão; nunca versionar |

## O que existe nos modelos

- `stg_outbox_events` (silver): eventos tipados e deduplicados por `event_id`.
- `dim_date` (gold): calendário 2024-01-01 a 2030-12-31 (2557 linhas), com feriados nacionais
  (seed `national_holidays`, gerado por `python analytics/ingestion/generate_holidays.py`) e período
  junino (`is_festa_junina_season`) parametrizado em `dbt_project.yml` (**definição de negócio a validar pelo autor**).

Dimensões e fatos de negócio ainda não existem: a modelagem dimensional é de autoria humana
([matriz de barramento](../docs/dados/matriz-de-barramento.md)).
