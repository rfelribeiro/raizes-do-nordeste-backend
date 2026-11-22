# analytics/ - pipeline do Data Warehouse

Pipeline analítico da Raízes do Nordeste: outbox (PostgreSQL) -> bronze (Parquet) -> silver e
gold (dbt + DuckDB). Arquitetura, convenções e LGPD: [docs/dados/README.md](../docs/dados/README.md).
Decisões: [ADR 0007](../docs/arquitetura/adr/0007-visao-analitica.md) e [ADR 0008](../docs/arquitetura/adr/0008-plataforma-analitica.md), [ADR 0009](../docs/arquitetura/adr/0009-nomenclatura-e-contratos-de-dados.md) e [ADR 0010](../docs/arquitetura/adr/0010-idioma-portugues.md) (nomes em português; código Python e variáveis de ambiente em inglês).
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
data/lake/bronze/outbox_eventos/dt=AAAA-MM-DD/<run_id>.parquet
data/lake/_estado/outbox_eventos.json        # marca d'água da extração
data/warehouse/raizes.duckdb                 # silver (schema silver) e gold (schema gold)
```

Consultar o resultado, por exemplo:

```bash
docker compose run --rm --no-deps --entrypoint "" analytics python -c \
  "import duckdb; print(duckdb.connect('/app/data/warehouse/raizes.duckdb', read_only=True).sql('select count(*) from gold.dim_tempo'))"
```

## Estrutura

```
ingestao/extrair_outbox.py   # extrator incremental (funções puras + I/O)
ingestao/gerar_feriados.py # gera o seed de feriados nacionais (algoritmo da Páscoa)
tests/                       # testes das funções puras
dbt/raizes_dw/               # projeto dbt: models/staging (silver), models/marts (gold), seeds
Dockerfile                   # imagem do serviço analytics (Python 3.14.10, usuário não-root)
requirements.in / .lock      # dependências travadas (geradas dentro de contêiner)
```

## Como funciona a extração

1. Lê `ultimo_id_sequencial` de `_estado/outbox_eventos.json` (0 se não existir).
2. Seleciona de `outbox_eventos` as linhas com `id_sequencial` maior que a marca d'água e
   `registrado_em` anterior a "agora - atraso" (padrão 5 s, `DW_EXTRACTION_LAG_SECONDS`).
   O atraso de segurança evita pular eventos de transações que confirmam fora de ordem; transações mais longas
   que o atraso de segurança continuam sendo um risco residual (ver ADR 0008).
3. Agrupa por data de captura (UTC) e grava um Parquet por partição (`dt=`), de forma atômica.
4. **Somente depois** de gravar tudo, atualiza a marca d'água (também de forma atômica).

É idempotente: sem eventos novos, nada é gravado. Se falhar antes do passo 4, a próxima execução
relê as mesmas linhas; a silver deduplica por `id_evento`, então não há dupla contagem.
A conexão usa as variáveis `POSTGRES_*` já usadas pela API; a senha nunca é logada.

## Bronze vazio

Antes de existir qualquer evento, o glob `bronze/outbox_eventos/*/*.parquet` não encontraria
arquivo e o dbt falharia. Solução: o extrator (e `--somente-esquema`, usado por `make dw-build`
e pela CI, sem acessar o banco) cria `dt=1970-01-01/_esquema_vazio.parquet`, um Parquet com 0 linhas
e o esquema do bronze. Assim `stg_outbox_eventos` funciona (e retorna 0 linhas) sem eventos.

## Variáveis de ambiente

| Variável | Uso | Padrão |
|---|---|---|
| `DW_DUCKDB_PATH` | arquivo DuckDB | `data/warehouse/raizes.duckdb` (no compose: `/app/data/warehouse/raizes.duckdb`) |
| `DW_LAKE_PATH` | raiz do lake | `data/lake` (no compose: `/app/data/lake`) |
| `DW_EXTRACTION_LAG_SECONDS` | atraso de segurança da extração | `5` |
| `ANALYTICS_PSEUDONYM_KEY` | segredo do HMAC de pseudonimização (gerado por `make setup`) | sem padrão; nunca versionar |

## O que existe nos modelos

- `stg_outbox_eventos` (silver): eventos tipados e deduplicados por `id_evento`.
- `dim_tempo` (gold): calendário 2024-01-01 a 2030-12-31 (2557 linhas), com feriados nacionais
  (seed `feriados_nacionais`, gerado por `python analytics/ingestao/gerar_feriados.py`) e período
  junino (`eh_periodo_junino`) parametrizado em `dbt_project.yml` (**definição de negócio a validar pelo autor**).

- Dimensões estáticas (gold, SCD 1, com membro -1): `dim_canal`, `dim_status_pedido`
  (valores do enum `OrderStatus`) e `dim_forma_pagamento` (valores de `PaymentMethod`).
- `dim_hora` (gold): grão minuto (1440 linhas + membro -1), `sk_hora` = HHMM. Limites de
  `periodo_dia` e janelas de `eh_pico` em `vars` do `dbt_project.yml` (**definição de negócio validada pelo autor em 2026-11-22 (D-063)**).
- `dim_unidade` (gold): mínima, só `id_unidade` dos eventos.
- `int_cliente_pseudonimo` (silver, modelo Python) e `dim_cliente` (gold): cliente mínimo e
  pseudonimizado (HMAC-SHA256 com `ANALYTICS_PSEUDONYM_KEY`; o DuckDB não tem HMAC nativo, por
  isso o modelo é Python). O id em claro fica só na silver. Membros -1 (sem cliente) e -2
  (anonimizado; só o membro, o processo fica como evolução). Sem a chave, o build falha com mensagem clara; na CI usa-se um valor fictício.
- `fct_pedido` (gold): um pedido, no status mais recente conhecido.
- `fct_tentativa_pagamento` (gold): uma tentativa de pagamento com resultado (aprovada ou recusada).

Os fatos 2 (`fct_pedido`) e 4 (`fct_tentativa_pagamento`) da matriz foram implementados pela IA
seguindo a modelagem do autor (D-062). Lacunas, por falta do dado nos eventos: `numero_pedido`,
`qtd_itens`, campanha, colaborador, atributos de unidade (nome, cidade, uf, região, formato) e de
cliente (faixa etária, perfil, cidade), `latencia_gateway_ms`, `dim_motivo` e as tentativas com
timeout (a tentativa `FALHA` não gera evento). Os demais fatos e dimensões continuam modelados, não implementados
([matriz de barramento](../docs/dados/matriz-de-barramento.md)).
