# Dicionário de dados

Catálogo dos objetos de banco e de dados do projeto e do contrato da API: convenções de nomes,
glossário de negócio (ponte português -> inglês para integrações) e a descrição de cada objeto
implementado. Decisão: [ADR 0010](../arquitetura/adr/0010-idioma-portugues.md) (tudo em
português; o dicionário e os contratos de dados do [ADR 0009](../arquitetura/adr/0009-nomenclatura-e-contratos-de-dados.md) seguem válidos).

> **Fonte de verdade.** O catálogo vivo é o **`dbt docs`** (`make dw-docs`, gera
> `analytics/dbt/raizes_dw/target/`). Para os objetos implementados, as **descrições escritas nos
> YAMLs do dbt** (`analytics/dbt/raizes_dw/models/**/_*.yml` e `seeds/_seeds.yml`) são a fonte de
> verdade; este documento as espelha em linguagem de leitura. Em caso de divergência, vale o dbt.
> Contratos verificáveis: [`contracts/`](../../contracts/README.md).

## Convenções

Tudo em **português**: contrato da API (rotas, campos JSON, enums) e objetos de banco, DW e eventos
(`snake_case`, sem acento). Os **valores** dos dados (ex.: "Natal", "janeiro") também ficam em
português.

**Exceções (decisão D-034, ADR 0010), mantidas em inglês:** identificadores de código Python
(classes, funções, variáveis, atributos) e variáveis de ambiente (convenção operacional; as
`POSTGRES_*` são fixas das imagens), por exemplo `DW_EXTRACTION_LAG_SECONDS`.

| Regra | Convenção | Exemplo |
|---|---|---|
| Tabelas | singular nas dimensões e fatos; prefixos `stg_` (silver), `int_` (intermediária), `dim_`, `fct_` | `stg_outbox_eventos`, `dim_tempo`, `fct_item_pedido` |
| Chave substituta | `sk_<entidade>` | `sk_unidade`, `sk_produto` |
| Chave natural | `id_<entidade>` | `id_unidade`, `id_cliente` |
| Chave estrangeira no fato | `sk_<dimensão>` | `fct_item_pedido.sk_produto` |
| Timestamps | `*_em`, UTC, `timestamptz` | `ocorrido_em`, `registrado_em` |
| Datas | `data_*` | `data_feriado`, `data_abertura` |
| Booleanos | `eh_*` / `tem_*` | `eh_fim_de_semana`, `tem_desconto` |
| Valores monetários | `valor_*`, `numeric(12,2)`, BRL | `valor_liquido` |
| Quantidades | `qtd_*` | `qtd_saldo` |
| Durações | `duracao_*_s` ou `*_ms` | `duracao_preparo_s`, `latencia_gateway_ms` |
| SCD tipo 2 | `valido_de`, `valido_ate` (9999-12-31 na vigente), `eh_atual` | |
| Membros especiais | `-1` não identificado / não se aplica; `-2` anonimizado (LGPD) | `sk_cliente = -2` |

Exceção de chave: `dim_tempo` usa `sk_data` (inteiro AAAAMMDD, chave inteligente usual em
calendário), e não um sequencial.

## Glossário de negócio (português -> inglês, ponte para integrações)

Os nomes oficiais são os em português. A coluna da direita serve a parceiros e ferramentas
externas que usem o vocabulário de engenharia de dados em inglês.

| Português (nome oficial) | Inglês (ponte) |
|---|---|
| Matriz / franqueadora | headquarters / franchisor |
| Franqueado | franchisee |
| Unidade (`unidade`) | store |
| Pedido (`pedido`) | order |
| Item de pedido (`item_pedido`) | order item |
| Número do pedido (`numero_pedido`) | order number |
| Canal (`canal`) | channel |
| Totem (autoatendimento) | kiosk |
| Balcão | counter |
| Retirada (pick-up) | pick-up |
| Cliente (`cliente`) | customer |
| Colaborador (`colaborador`) | employee |
| Produto (`produto`) | product |
| Forma de pagamento (`forma_pagamento`) | payment method |
| Tentativa de pagamento (`tentativa_pagamento`) | payment attempt |
| Campanha (`campanha`) | campaign |
| Motivo (`motivo`) | reason |
| Finalidade (LGPD) (`finalidade`) | processing purpose |
| Base legal (`base_legal`) | legal basis |
| Consentimento (`consentimento`) | consent |
| Pontos de fidelidade (`pontos`) | loyalty points |
| Estoque (`estoque`) | inventory |
| Saldo de estoque (`qtd_saldo`) | on-hand balance |
| Ruptura (`eh_ruptura`) | stockout |
| Período junino (`eh_periodo_junino`) | festa junina season |
| Feriado nacional (`eh_feriado_nacional`) | national holiday |
| Faixa etária (`faixa_etaria`) | age band |
| Formato da unidade (`formato_unidade`) | store format |
| Sazonal / temporada (`eh_sazonal`, `temporada`) | seasonal / season |
| Valor bruto / desconto / líquido | gross / discount / net amount |
| Evento de domínio | domain event |
| Agregado | aggregate |
| Tipo de evento (`tipo_evento`) | event type |

## Contrato da API

Convenções da interface HTTP, também em português (ADR 0010). Os identificadores de código Python
ficam em inglês; apenas o que trafega na rede segue a regra abaixo. Formato de erro: ADR 0011 e
[docs/api/README.md](../api/README.md).

| Item | Convenção | Exemplo |
|---|---|---|
| Rotas | plural, minúsculas, em português | `/auth`, `/usuarios`, `/unidades`, `/produtos`, `/estoques`, `/pedidos` (pagamento como subrecurso: `/pedidos/{id}/pagamentos`), `/fidelidade`, `/consentimentos`, `/auditoria` |
| Campos JSON | `camelCase` em português | `canalPedido`, `clienteId`, `unidadeId`, `itens`, `produtoId`, `quantidade`, `formaPagamento`, `precoUnitario`, `criadoEm` |
| Datas e horas | ISO-8601 em UTC; campos de instante terminam em `Em` | `criadoEm`: `2026-02-05T12:00:00Z` |
| Enums | MAIÚSCULAS, sem acento, `_` entre palavras | `AGUARDANDO_PAGAMENTO` |
| Canal do pedido | enum `canalPedido` do roteiro da trilha | `APP`, `TOTEM`, `BALCAO`, `PICKUP`, `WEB` |
| Paginação | `?page=1&limit=10` (nomes do roteiro) | `GET /pedidos?page=1&limit=10` |
| Erros | JSON padrão `error`, `message`, `details`, `timestamp`, `path`, `requestId` | ver [docs/api/README.md](../api/README.md) |

Os valores do enum `canalPedido` são os mesmos de `dim_canal.nome_canal` no DW.

## Objetos implementados

### `outbox_eventos` (PostgreSQL, OLTP)

Outbox de eventos de domínio, gravada na mesma transação do caso de uso. Contrato:
[`contracts/events/outbox_eventos.contract.yaml`](../../contracts/events/outbox_eventos.contract.yaml).
Migração: `migrations/versions/20261102_1615_0001_cria_outbox_eventos.py`.

| Coluna | Tipo | Nulo? | Descrição | Regra / exemplo |
|---|---|---|---|---|
| `id_evento` | uuid | não | Identificador único do evento | UUID v4 gerado pelo domínio; chave primária |
| `tipo_evento` | text | não | Nome estável do evento | `snake_case` `<entidade>_<particípio>` (`pedido_criado`) |
| `versao_schema` | integer | não | Versão do formato do payload | >= 1 |
| `tipo_agregado` | text | não | Tipo do agregado de negócio | `pedido` |
| `id_agregado` | text | não | Identificador do agregado | `"42"`; nunca dado pessoal |
| `payload` | jsonb | não | Conteúdo específico do evento | objeto JSON, sem PII em claro |
| `ocorrido_em` | timestamptz | não | Instante do fato de negócio | UTC |
| `registrado_em` | timestamptz | não | Instante em que a outbox registrou o evento | UTC; `default now()` |
| `id_sequencial` | bigint | não | Ordem de captura | identidade `ALWAYS`; marca d'água da extração; índice `ix_outbox_eventos_id_sequencial` |

### `stg_outbox_eventos` (silver, DuckDB)

Eventos tipados e deduplicados por `id_evento` (mantém a primeira captura, menor `id_sequencial`).
Origem: bronze `data/lake/bronze/outbox_eventos/`. Contrato do dbt imposto (`contract.enforced`).

| Coluna | Tipo | Nulo? | Descrição | Regra / exemplo |
|---|---|---|---|---|
| `id_evento` | uuid | não | Identificador único do evento | único |
| `tipo_evento` | varchar | não | Nome estável do evento | `pedido_criado` |
| `versao_schema` | integer | não | Versão do formato do payload | >= 1 |
| `tipo_agregado` | varchar | não | Tipo do agregado | `pedido` |
| `id_agregado` | varchar | não | Identificador do agregado | `"42"` |
| `payload` | json | sim | Conteúdo do evento | sem PII em claro |
| `ocorrido_em` | timestamp with time zone | não | Instante do fato (UTC) | |
| `registrado_em` | timestamp with time zone | não | Instante de captura na outbox (UTC) | |
| `id_sequencial` | bigint | não | Ordem de captura (marca d'água) | |
| `data_particao` | date | sim | Data (UTC) da partição `dt=` do bronze em que o evento chegou | derivada de `registrado_em` |

### `dim_tempo` (gold, DuckDB)

Dimensão de tempo (data): calendário diário de 2024-01-01 a 2030-12-31 (2557 linhas), data civil
em America/Recife. Contrato do dbt imposto. Texto dos nomes em português.

| Coluna | Tipo | Nulo? | Descrição | Regra / exemplo |
|---|---|---|---|---|
| `sk_data` | integer | não | Chave substituta AAAAMMDD | `20261225`; única |
| `data` | date | não | Data completa (chave natural) | `2026-12-25`; única |
| `ano` | integer | não | Ano | `2026` |
| `trimestre` | integer | não | Trimestre | 1 a 4 |
| `mes` | integer | não | Mês | 1 a 12 |
| `nome_mes` | varchar | sim | Nome do mês em português | `dezembro` |
| `dia_mes` | integer | não | Dia do mês | 1 a 31 |
| `dia_semana` | integer | não | Dia da semana ISO | 1 = segunda ... 7 = domingo |
| `nome_dia_semana` | varchar | sim | Nome do dia da semana em português | `sexta-feira` |
| `eh_fim_de_semana` | boolean | não | Sábado ou domingo | |
| `eh_feriado_nacional` | boolean | não | Consta em `feriados_nacionais` | |
| `nome_feriado` | varchar | sim | Nome do feriado em português | `Natal`; nulo se não for feriado |
| `eh_periodo_junino` | boolean | não | Dentro do período junino | variáveis dbt `periodo_junino_inicio`/`periodo_junino_fim` (padrão 06-01 a 07-31); **definição de negócio a validar pelo autor** |

### `dim_canal` (gold, DuckDB)

Canal do pedido (SCD 1, estática, 6 linhas com o membro -1). Contrato imposto.

| Coluna | Tipo | Nulo? | Descrição | Regra / exemplo |
|---|---|---|---|---|
| `sk_canal` | integer | não | Chave substituta | -1 não identificado; 1 a 5; única |
| `nome_canal` | varchar | não | Nome do canal (enum `canalPedido`) | `APP`, `TOTEM`, `BALCAO`, `PICKUP`, `WEB`; única |
| `tipo_canal` | varchar | não | Tipo do canal | `digital` (APP, WEB, PICKUP) ou `presencial` (TOTEM, BALCAO) |

### `dim_status_pedido` (gold, DuckDB)

Status do pedido (SCD 1, estática). Valores do enum `OrderStatus`. Contrato imposto.

| Coluna | Tipo | Nulo? | Descrição | Regra / exemplo |
|---|---|---|---|---|
| `sk_status_pedido` | integer | não | Chave substituta | -1 não identificado; 1 a 6; única |
| `nome_status_pedido` | varchar | não | Nome do status | `AGUARDANDO_PAGAMENTO`, `PAGO`, `EM_PREPARO`, `PRONTO`, `ENTREGUE`, `CANCELADO` |
| `ordem_fluxo` | integer | sim | Posição no fluxo | 1 a 6; nulo no -1 |
| `eh_final` | boolean | não | Status final | verdadeiro em `ENTREGUE` e `CANCELADO` |

### `dim_forma_pagamento` (gold, DuckDB)

Forma de pagamento (SCD 1, estática). Valores do enum `PaymentMethod`. Contrato imposto.

| Coluna | Tipo | Nulo? | Descrição | Regra / exemplo |
|---|---|---|---|---|
| `sk_forma_pagamento` | integer | não | Chave substituta | -1 não identificado; 1 a 3; única |
| `nome_forma_pagamento` | varchar | não | Nome da forma de pagamento | `PIX`, `CREDITO`, `DEBITO` |
| `grupo_forma_pagamento` | varchar | não | Agrupamento | `pix` ou `cartão` |

### `dim_hora` (gold, DuckDB)

Hora do dia no grão minuto: 1440 linhas + membro -1, hora local de America/Recife. Contrato imposto.

| Coluna | Tipo | Nulo? | Descrição | Regra / exemplo |
|---|---|---|---|---|
| `sk_hora` | integer | não | Chave substituta HHMM | `1430`; -1 não identificado; única |
| `hora` | integer | sim | Hora | 0 a 23; nulo no -1 |
| `minuto` | integer | sim | Minuto | 0 a 59; nulo no -1 |
| `periodo_dia` | varchar | não | Período do dia | `madrugada` (00:00), `café da manhã` (06:00), `almoço` (11:00), `tarde` (15:00), `noite` (18:00); vars `periodo_*_inicio`; **validada pelo autor em 2026-11-22 (D-063)** |
| `eh_pico` | boolean | não | Janela de pico | 11:30-14:00 e 18:00-20:30 (vars `pico_*`); **validada pelo autor em 2026-11-22 (D-063)** |

### `dim_unidade` (gold, DuckDB)

Unidade, MÍNIMA: só o id que aparece nos eventos. Lacuna: nome, cidade, uf, região e formato exigem evento de cadastro de unidade. Sem SCD 2. Contrato imposto.

| Coluna | Tipo | Nulo? | Descrição | Regra / exemplo |
|---|---|---|---|---|
| `sk_unidade` | integer | não | Chave substituta (ordem de primeira aparição) | -1 não identificado; única |
| `id_unidade` | varchar | sim | Id da unidade (UUID em texto) | nulo só no -1 |

### `int_cliente_pseudonimo` (silver, modelo Python)

Mapa interno id do cliente -> chave substituta e pseudônimo. Guarda o id em claro; **não** é exposta na gold. Sem contrato (modelos Python não o suportam).

| Coluna | Tipo | Nulo? | Descrição | Regra / exemplo |
|---|---|---|---|---|
| `sk_cliente` | integer | não | Chave substituta (ordem de primeira aparição) | única |
| `id_cliente` | varchar | não | Id do cliente (UUID em texto) | do evento `pedido_criado` |
| `id_cliente_pseudonimo` | varchar | não | HMAC-SHA256 (hex) do id | chave `ANALYTICS_PSEUDONYM_KEY` |

### `dim_cliente` (gold, DuckDB)

Cliente, MÍNIMO e pseudonimizado (sem o id em claro). Lacuna: faixa etária, perfil, cidade, uf e adesão não existem nos eventos. Sem SCD 2. Contrato imposto.

| Coluna | Tipo | Nulo? | Descrição | Regra / exemplo |
|---|---|---|---|---|
| `sk_cliente` | integer | não | Chave substituta | -1 não identificado; -2 anonimizado (só o membro); única |
| `id_cliente_pseudonimo` | varchar | sim | HMAC-SHA256 (hex) do id do cliente | nulo em -1 e -2 |
| `situacao_cliente` | varchar | não | Situação | `identificado`, `não identificado`, `anonimizado` |

### `fct_pedido` (gold, DuckDB)

Grão: um pedido, no status mais recente conhecido (último `status_novo` por `ocorrido_em`, desempate por `id_sequencial`; sem mudança, o status do `pedido_criado`). Data e hora locais de America/Recife. Contrato imposto. Lacunas: `numero_pedido`, `sk_campanha`, `sk_colaborador`, `qtd_itens`.

| Coluna | Tipo | Nulo? | Descrição | Regra / exemplo |
|---|---|---|---|---|
| `id_pedido` | varchar | não | Id do pedido (dimensão degenerada) | única (grão) |
| `sk_data` | integer | não | Data de criação | -> `dim_tempo.sk_data` |
| `sk_hora` | integer | não | Hora local de criação | -> `dim_hora.sk_hora` |
| `sk_unidade` | integer | não | Unidade | -> `dim_unidade`; -1 se desconhecida |
| `sk_canal` | integer | não | Canal | -> `dim_canal` |
| `sk_cliente` | integer | não | Cliente | -> `dim_cliente`; -1 sem cliente |
| `sk_status_pedido` | integer | não | Status atual | -> `dim_status_pedido` |
| `valor_bruto` | decimal(12,2) | não | Valor total do pedido (BRL) | `valor_total` do evento |
| `valor_desconto` | decimal(12,2) | não | Desconto | sempre 0 no MVP |
| `valor_liquido` | decimal(12,2) | não | Bruto menos desconto |  |
| `criado_em` | timestamptz | não | Instante de criação (UTC) |  |

### `fct_tentativa_pagamento` (gold, DuckDB)

Grão: uma tentativa de pagamento com resultado (aprovada ou recusada). Contrato imposto. Lacunas: `latencia_gateway_ms`, `dim_motivo`, tentativas com timeout (`FALHA` não gera evento).

| Coluna | Tipo | Nulo? | Descrição | Regra / exemplo |
|---|---|---|---|---|
| `id_pedido` | varchar | não | Id do pedido (dimensão degenerada) | com `numero_tentativa`, única (teste singular) |
| `numero_tentativa` | integer | não | Número da tentativa no pedido |  |
| `resultado` | varchar | não | Resultado (degenerado) | `APROVADO` ou `RECUSADO` |
| `motivo_recusa` | varchar | sim | Motivo da recusa (degenerado) | nulo se aprovado |
| `sk_data` | integer | não | Data do resultado | -> `dim_tempo` |
| `sk_hora` | integer | não | Hora local do resultado | -> `dim_hora` |
| `sk_unidade` | integer | não | Unidade | -> `dim_unidade` |
| `sk_canal` | integer | não | Canal | -> `dim_canal` |
| `sk_forma_pagamento` | integer | não | Forma de pagamento | -> `dim_forma_pagamento` |
| `sk_cliente` | integer | não | Cliente (via `pedido_criado`) | -> `dim_cliente`; -1 sem cliente |
| `valor_solicitado` | decimal(12,2) | não | Valor cobrado |  |
| `valor_aprovado` | decimal(12,2) | não | Valor aprovado | igual ao solicitado se aprovado; 0 se recusado |
| `ocorrido_em` | timestamptz | não | Instante do resultado (UTC) |  |

### `feriados_nacionais` (seed do dbt, silver)

Feriados nacionais do Brasil (2024-2030), gerados por `analytics/ingestao/gerar_feriados.py`.

| Coluna | Tipo | Nulo? | Descrição | Regra / exemplo |
|---|---|---|---|---|
| `data_feriado` | date | não | Data do feriado | `2026-12-25` |
| `nome_feriado` | varchar | não | Nome do feriado em português | `Natal` |
| `tipo_feriado` | varchar | não | Tipo do feriado | por ora sempre `nacional` |

### Bronze (arquivos Parquet)

`data/lake/bronze/outbox_eventos/dt=AAAA-MM-DD/<run_id>.parquet`: espelha `outbox_eventos` com
todas as datas em texto ISO-8601 UTC e `payload` em texto JSON (colunas: `id_evento`,
`tipo_evento`, `versao_schema`, `tipo_agregado`, `id_agregado`, `payload`, `ocorrido_em`,
`registrado_em`, `id_sequencial`). Estado da extração: `data/lake/_estado/outbox_eventos.json`.
Parquet de esquema vazio: `dt=1970-01-01/_esquema_vazio.parquet`. Detalhes em
[`analytics/README.md`](../../analytics/README.md).

## Objetos planejados

Implementados: `fct_pedido`, `fct_tentativa_pagamento` e as dimensões acima (D-062). Os demais ainda não; nomes, grãos e medidas estão na
[matriz de barramento](matriz-de-barramento.md) (autoria humana).

- **Fatos:** `fct_item_pedido`, `fct_pedido`, `fct_ciclo_pedido`, `fct_tentativa_pagamento`,
  `fct_movimentacao_estoque`, `fct_saldo_estoque_diario`, `fct_movimento_pontos`,
  `fct_operacao_sensivel`, `fct_consentimento_diario`.
- **Dimensões (implementadas: tempo, hora, canal, status, forma de pagamento, unidade e cliente, as duas últimas mínimas):** `dim_tempo`, `dim_hora`, `dim_unidade` (mínima), `dim_produto`,
  `dim_canal` (`APP`, `TOTEM`, `BALCAO`, `PICKUP`, `WEB`), `dim_cliente` (mínima), `dim_forma_pagamento`,
  `dim_campanha`, `dim_colaborador`, `dim_status_pedido`, `dim_motivo`, `dim_finalidade`.
- **Dimensão degenerada:** `numero_pedido`.

Cada objeto planejado ganhará sua tabela neste dicionário, e sua descrição no dbt, ao ser
implementado.
