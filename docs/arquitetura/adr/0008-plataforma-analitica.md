# ADR 0008 - Plataforma analítica: DuckDB + Parquet, Outbox, Kimball e dbt-core

- **Status:** aceita (item "nomes de objetos de banco em português": proposta, pendente de validação humana)
- **Data:** 2026-11-02

## Contexto

O [ADR 0007](0007-visao-analitica.md) define a visão (DW com margem para Lakehouse). Faltam as
escolhas de plataforma. Restrições: o repositório é público (nenhum segredo nem dado pessoal), o
examinador precisa reproduzir exatamente o que roda localmente, e tudo deve subir por Docker
Compose e `make`, sem serviços pagos.

## Decisão

Para cada item a IA recomendou uma opção e o humano escolheu explicitamente:

| Tema | Escolha do humano | Observação |
|---|---|---|
| Motor e formato | **DuckDB + Parquet** em arquitetura medallion (bronze/silver/gold) | Embutido, sem servidor; lê e escreve Parquet nativamente. |
| Captura OLTP -> analítico | **Outbox de eventos de domínio** | Tabela `outbox_eventos` gravada na MESMA transação do caso de uso; extrator incremental por marca d'água (`id_sequencial`). |
| Modelagem do gold | **Kimball (esquema estrela)** | Dimensões `dim_*` e fatos `fct_*`, chaves substitutas, membro desconhecido -1. |
| Transformações | **dbt-core** (adapter dbt-duckdb) | SQL versionado, testes de dados, documentação e linhagem. |

Versões travadas em `analytics/requirements.lock` (gerado dentro de contêiner): dbt-core 1.12.6,
dbt-duckdb 1.11.1, duckdb 1.5.6, psycopg 3.3.6. Imagem `analytics`: **Python 3.14.10**, a mesma da API
(o dbt resolveu e executou normalmente no 3.14, então não foi necessário recuar de versão).

### Alternativas consideradas

- **Captura:** extração batch incremental direto das tabelas de negócio (por `atualizado_em`):
  simples, mas perde deleções e estados intermediários e acopla o analítico ao esquema transacional.
  **CDC com Debezium** (log do PostgreSQL -> Kafka): é a evolução conceitual da outbox (fase 4 do
  roadmap), descartada agora por exigir Kafka/Connect, excessivo para o escopo.
- **Modelagem:** Data Vault + estrela (mais rastreável e flexível para muitas fontes, porém mais
  tabelas e complexidade para uma fonte única) e OBT (uma tabela larga: rápida de montar, mas
  redundante e pouco reutilizável entre processos de negócio).
- **Transformações:** SQL puro + scripts Python (menos dependências, sem testes/linhagem/docs
  padronizados) e Polars/Pandas (bons para dados em memória, mas o código fica imperativo e preso
  à biblioteca; SQL declarativo é mais portável entre motores).
- **Motor:** PostgreSQL em schema separado (zero infraestrutura nova, porém mistura OLTP e OLAP,
  compete por recursos com a API e não treina o caminho para o lake) e ClickHouse (excelente
  desempenho analítico, mas é um servidor adicional a operar, excessivo para o volume do projeto).

### Decisão da IA, pendente de validação humana: nomes em português

Objetos de banco (tabelas, colunas, modelos dbt) em **português, `snake_case`, sem acento**
(`outbox_eventos`, `id_evento`, `dim_tempo`, `fct_*`). Identificadores de código Python ficam em
inglês. Motivo: o domínio e os termos do estudo de caso são em português e quem consome o
analítico é gente de negócio. Esta decisão ainda **não foi validada pelo autor**.

## Consequências

- (+) Ambiente 100% local e reprodutível (`make dw`); formatos abertos; dbt agnóstico ao motor.
- (+) A outbox dá atomicidade (evento só existe se o negócio foi confirmado) e histórico imutável.
- (-) A outbox exige disciplina: todo caso de uso relevante precisa publicar seus eventos.
- (-) A extração por `id_sequencial` pode perder eventos de transações longas que confirmam fora
  de ordem; mitigado por uma defasagem de segurança (padrão 5 s), com risco residual documentado.
- (-) DuckDB é embutido e de escritor único: serve a análise local, não a concorrência de produção
  (resolvida nas fases 2 e 3 do roadmap).
- (-) Eventos são permanentes no bronze: a regra "sem PII em claro no payload" é inegociável (ver docs/dados/README.md).

**Autoria da decisão:** **conjunta.** A IA recomendou cada item e o humano escolheu explicitamente.
Nomes de objetos de banco em português: decisão da IA, pendente de validação.
