# Dicionário de dados

Catálogo dos objetos de banco e de dados do projeto: convenções de nomes, glossário de negócio
(português -> inglês) e a descrição de cada objeto implementado. Decisão: [ADR 0009](../arquitetura/adr/0009-nomenclatura-e-contratos-de-dados.md).

> **Fonte de verdade.** O catálogo vivo é o **`dbt docs`** (`make dw-docs`, gera
> `analytics/dbt/raizes_dw/target/`). Para os objetos implementados, as **descrições escritas nos
> YAMLs do dbt** (`analytics/dbt/raizes_dw/models/**/_*.yml` e `seeds/_seeds.yml`) são a fonte de
> verdade; este documento as espelha em linguagem de leitura. Em caso de divergência, vale o dbt.
> Contratos verificáveis: [`contracts/`](../../contracts/README.md).

## Convenções

Objetos em inglês, `snake_case`. Documentação e **valores** dos dados (ex.: "Natal", "janeiro")
permanecem em português.

| Regra | Convenção | Exemplo |
|---|---|---|
| Tabelas | singular nas dimensões e fatos; prefixos `stg_` (silver), `int_` (intermediária), `dim_`, `fct_` | `stg_outbox_events`, `dim_date`, `fct_order_item` |
| Chave substituta | `<entidade>_sk` | `store_sk`, `product_sk` |
| Chave natural | `<entidade>_id` | `store_id`, `customer_id` |
| Chave estrangeira no fato | `<dimensão>_sk` | `fct_order_item.product_sk` |
| Timestamps | `*_at`, UTC, `timestamptz` | `occurred_at`, `recorded_at` |
| Datas | `*_date` | `holiday_date`, `opened_date` |
| Booleanos | `is_*` / `has_*` | `is_weekend`, `has_discount` |
| Valores monetários | `*_amount`, `numeric(12,2)`, BRL | `net_amount` |
| Quantidades | `*_qty` | `on_hand_qty` |
| Durações | `*_seconds` ou `*_ms` | `preparation_seconds`, `gateway_latency_ms` |
| SCD tipo 2 | `valid_from`, `valid_to` (9999-12-31 na vigente), `is_current` | |
| Membros especiais | `-1` desconhecido / não se aplica; `-2` anonimizado (LGPD) | `customer_sk = -2` |

Exceção: `dim_date` usa `date_key` (inteiro AAAAMMDD, chave inteligente usual em calendário) no
lugar de `date_sk`. Variáveis de ambiente: `DW_*` e `ANALYTICS_*`, em maiúsculas, em inglês
(ex.: `DW_EXTRACTION_LAG_SECONDS`).

## Glossário de negócio (português -> inglês)

| Português | Inglês (termo técnico) |
|---|---|
| Matriz / franqueadora | headquarters / franchisor |
| Franqueado | franchisee |
| Unidade / loja | store (`store`) |
| Pedido | order (`order`) |
| Item de pedido | order item (`order_item`) |
| Número do pedido | order number (`order_number`) |
| Canal | channel (`channel`) |
| Totem (autoatendimento) | kiosk |
| Balcão | counter |
| Retirada (pick-up) | pick-up |
| Cliente | customer (`customer`) |
| Colaborador | employee (`employee`) |
| Produto | product (`product`) |
| Forma de pagamento | payment method (`payment_method`) |
| Tentativa de pagamento | payment attempt (`payment_attempt`) |
| Campanha | campaign (`campaign`) |
| Motivo | reason (`reason`) |
| Finalidade (LGPD) | processing purpose (`processing_purpose`) |
| Base legal | legal basis (`legal_basis`) |
| Consentimento | consent (`consent`) |
| Pontos de fidelidade | loyalty points (`loyalty_points`) |
| Estoque | inventory (`inventory`) |
| Saldo (de estoque) | on-hand balance (`on_hand_qty`) |
| Ruptura | stockout (`is_stockout`) |
| Período junino | festa junina season (`is_festa_junina_season`) |
| Feriado nacional | national holiday (`national_holiday`) |
| Faixa etária | age band (`age_band`) |
| Formato (da unidade) | store format (`store_format`) |
| Sazonal / temporada | seasonal / season (`is_seasonal`, `season`) |
| Valor bruto / desconto / líquido | gross / discount / net amount |
| Evento de domínio | domain event |
| Agregado | aggregate |

## Objetos implementados

### `outbox_events` (PostgreSQL, OLTP)

Outbox de eventos de domínio, gravada na mesma transação do caso de uso. Contrato:
[`contracts/events/outbox_events.contract.yaml`](../../contracts/events/outbox_events.contract.yaml).
Migração: `migrations/versions/20261102_1615_0001_create_outbox_events.py`.

| Coluna | Tipo | Nulo? | Descrição | Regra / exemplo |
|---|---|---|---|---|
| `event_id` | uuid | não | Identificador único do evento | UUID v4 gerado pelo domínio; chave primária |
| `event_type` | text | não | Nome estável do evento | `snake_case` (`order_created`) |
| `schema_version` | integer | não | Versão do formato do payload | >= 1 |
| `aggregate_type` | text | não | Tipo do agregado de negócio | `order` |
| `aggregate_id` | text | não | Identificador do agregado | `"42"`; nunca dado pessoal |
| `payload` | jsonb | não | Conteúdo específico do evento | objeto JSON, sem PII em claro |
| `occurred_at` | timestamptz | não | Instante do fato de negócio | UTC |
| `recorded_at` | timestamptz | não | Instante em que a outbox registrou o evento | UTC; `default now()` |
| `sequence_id` | bigint | não | Ordem de captura | identidade `ALWAYS`; marca d'água da extração; índice `ix_outbox_events_sequence_id` |

### `stg_outbox_events` (silver, DuckDB)

Eventos tipados e deduplicados por `event_id` (mantém a primeira captura, menor `sequence_id`).
Origem: bronze `data/lake/bronze/outbox_events/`. Contrato do dbt imposto (`contract.enforced`).

| Coluna | Tipo | Nulo? | Descrição | Regra / exemplo |
|---|---|---|---|---|
| `event_id` | uuid | não | Identificador único do evento | único |
| `event_type` | varchar | não | Nome estável do evento | `order_created` |
| `schema_version` | integer | não | Versão do formato do payload | >= 1 |
| `aggregate_type` | varchar | não | Tipo do agregado | `order` |
| `aggregate_id` | varchar | não | Identificador do agregado | `"42"` |
| `payload` | json | sim | Conteúdo do evento | sem PII em claro |
| `occurred_at` | timestamp with time zone | não | Instante do fato (UTC) | |
| `recorded_at` | timestamp with time zone | não | Instante de captura na outbox (UTC) | |
| `sequence_id` | bigint | não | Ordem de captura (marca d'água) | |
| `partition_date` | date | sim | Data (UTC) da partição `dt=` do bronze em que o evento chegou | derivada de `recorded_at` |

### `dim_date` (gold, DuckDB)

Dimensão de data: calendário diário de 2024-01-01 a 2030-12-31 (2557 linhas), data civil em
America/Recife. Contrato do dbt imposto. Texto dos nomes em português.

| Coluna | Tipo | Nulo? | Descrição | Regra / exemplo |
|---|---|---|---|---|
| `date_key` | integer | não | Chave substituta AAAAMMDD | `20261225`; única |
| `full_date` | date | não | Data completa (chave natural) | `2026-12-25`; única |
| `year` | integer | não | Ano | `2026` |
| `quarter` | integer | não | Trimestre | 1 a 4 |
| `month` | integer | não | Mês | 1 a 12 |
| `month_name` | varchar | sim | Nome do mês em português | `dezembro` |
| `day_of_month` | integer | não | Dia do mês | 1 a 31 |
| `day_of_week` | integer | não | Dia da semana ISO | 1 = segunda ... 7 = domingo |
| `day_of_week_name` | varchar | sim | Nome do dia da semana em português | `sexta-feira` |
| `is_weekend` | boolean | não | Sábado ou domingo | |
| `is_national_holiday` | boolean | não | Consta em `national_holidays` | |
| `holiday_name` | varchar | sim | Nome do feriado em português | `Natal`; nulo se não for feriado |
| `is_festa_junina_season` | boolean | não | Dentro do período junino | variáveis dbt `festa_junina_season_start`/`_end` (padrão 06-01 a 07-31); **definição de negócio a validar pelo autor** |

### `national_holidays` (seed do dbt, silver)

Feriados nacionais do Brasil (2024-2030), gerados por `analytics/ingestion/generate_holidays.py`.

| Coluna | Tipo | Nulo? | Descrição | Regra / exemplo |
|---|---|---|---|---|
| `holiday_date` | date | não | Data do feriado | `2026-12-25` |
| `holiday_name` | varchar | não | Nome do feriado em português | `Natal` |
| `holiday_type` | varchar | não | Tipo do feriado | por ora sempre `national` |

### Bronze (arquivos Parquet)

`data/lake/bronze/outbox_events/dt=AAAA-MM-DD/<run_id>.parquet`: espelha `outbox_events` com todas
as datas em texto ISO-8601 UTC e `payload` em texto JSON (colunas: `event_id`, `event_type`,
`schema_version`, `aggregate_type`, `aggregate_id`, `payload`, `occurred_at`, `recorded_at`,
`sequence_id`). Estado da extração: `data/lake/_state/outbox_events.json`. Detalhes em
[`analytics/README.md`](../../analytics/README.md).

## Objetos planejados

Ainda não implementados; nomes, grãos e medidas estão na
[matriz de barramento](matriz-de-barramento.md) (autoria humana).

- **Fatos:** `fct_order_item`, `fct_order`, `fct_order_lifecycle`, `fct_payment_attempt`,
  `fct_inventory_movement`, `fct_inventory_daily_snapshot`, `fct_loyalty_points_movement`,
  `fct_sensitive_operation`, `fct_consent_daily_snapshot`.
- **Dimensões:** `dim_date` (implementada), `dim_time_of_day`, `dim_store`, `dim_product`,
  `dim_channel`, `dim_customer`, `dim_payment_method`, `dim_campaign`, `dim_employee`,
  `dim_order_status`, `dim_reason`, `dim_processing_purpose`.
- **Dimensão degenerada:** `order_number`.

Cada objeto planejado ganhará sua tabela neste dicionário, e sua descrição no dbt, ao ser
implementado.
