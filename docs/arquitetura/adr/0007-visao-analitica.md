# ADR 0007 - Visão analítica: Data Warehouse com margem para Lakehouse

- **Status:** aceita
- **Data:** 2026-11-02

## Contexto

O estudo de caso pede à matriz vendas por unidade e por região, produtos mais consumidos,
relatórios financeiros, dados consolidados para decisões estratégicas, auditoria de operações
sensíveis e campanhas segmentadas de fidelidade. Atender isso só com consultas no banco
transacional mistura cargas diferentes e limita a evolução.

O autor, profissional de dados, quer dar ao projeto uma identidade analítica. Nas palavras dele:

> "não é uma empresa de tecnologia, mas dados são essenciais para qualquer empresa"

O objetivo não é desvirtuar o projeto (a API continua sendo o núcleo da entrega), e sim trazer a
visão pessoal do arquiteto escolhido para a solução.

## Decisão

A identidade analítica do projeto é **um Data Warehouse dimensional, construído de modo a poder
evoluir para um Lakehouse**: armazenamento em formatos abertos (Parquet), camadas
bronze/silver/gold (medallion), transformações declarativas e versionadas, e um desenho que
troca o motor e o armazenamento sem reescrever os modelos.

A camada analítica fica em `analytics/` e documentada em `docs/dados/`. Os detalhes técnicos
estão no [ADR 0008](0008-plataforma-analitica.md). A modelagem dimensional de negócio (matriz de
barramento, grãos, fatos, dimensões e SCD) é de **autoria humana**.

## Alternativas consideradas

- Não ter camada analítica e atender os relatórios por consultas no PostgreSQL: mais simples,
  mas não expressa a visão de dados do autor e acopla análise e operação.
- Apenas views/materialized views no PostgreSQL: resolve relatórios pontuais, sem histórico
  imutável nem caminho de evolução.

## Consequências

- (+) Projeto com identidade própria e narrativa coerente: operação (OLTP) e análise (OLAP) separadas.
- (+) Caminho de evolução em fases até Lakehouse sem refazer a modelagem.
- (-) Mais peças para manter e para o examinador reproduzir (mitigado: tudo via `make dw`, em Docker).
- (-) O escopo exige disciplina: a camada analítica não pode atrasar a API nem os requisitos do estudo de caso.

**Autoria da decisão:** **humana.** A visão e a justificativa são do arquiteto; a IA apenas redigiu o registro.
