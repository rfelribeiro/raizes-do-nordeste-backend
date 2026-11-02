# ADR 0006 - Registro do uso de IA

- **Status:** aceita
- **Data:** 2026-11-02

## Contexto

O projeto usa IA de forma intensa e o uso deve ser transparente e auditável, separando o que foi decisão humana do que foi proposta da IA.

## Decisão

- **Exportação automática das conversas** com a IA (hooks do Claude Code) para `docs/uso-de-ia/`, com redação de dados sensíveis.
- **Log de decisões humano × IA**, mantido em `docs/uso-de-ia/`, registrando cada decisão, quem propôs e quem decidiu.

## Alternativas consideradas

- Registro manual: sujeito a esquecimento.
- Não registrar: contraria a decisão de transparência.

## Consequências

- (+) Rastreabilidade completa e baixo esforço contínuo.
- (-) Exige redação cuidadosa para não expor dados pessoais (ver ADR 0005).

**Autoria da decisão:** **decisão humana** (registrar tudo); mecanismo proposto pela IA.
