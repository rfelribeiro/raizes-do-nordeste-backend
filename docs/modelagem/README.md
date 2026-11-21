# Modelagem

Modelagem do sistema (seção 4 do documento principal): casos de uso, diagrama de classes, DER
(modelo de dados) e diagramas de sequência e de estado (ex.: ciclo de vida do pedido).

## Índice

| Artefato | Situação |
|---|---|
| [DER do banco transacional (PostgreSQL)](der.md) | Produzido |
| [Casos de uso](casos-de-uso.md) (diagrama, 11 descrições detalhadas e 16 resumidas) | Produzido |
| [Diagramas de classes](classes.md) (domínio e camada de aplicação com portas) | Produzido |
| [Diagramas de sequência](sequencia.md) (Realizar Pedido, Solicitar Pagamento, Atualizar Status) | Produzido |
| Diagrama de estados (ciclo de vida do pedido) | Produzido: [seção 5.1 dos requisitos](../requisitos/README.md#51-máquina-de-estados-do-pedido) |

## Dois modelos, dois propósitos

- **DER do OLTP:** modelo relacional normalizado do banco transacional (PostgreSQL) que a API usa.
  Está em [der.md](der.md).
- **Modelo dimensional do DW:** esquema estrela (Kimball) da camada analítica, no DuckDB. É um
  modelo à parte, derivado dos eventos de domínio, e é de **autoria humana**: matriz de
  barramento, grãos, fatos, dimensões e SCD ficam em
  [docs/dados/matriz-de-barramento.md](../dados/matriz-de-barramento.md). Os nomes técnicos dos objetos estão em português (D-034, [ADR 0010](../arquitetura/adr/0010-idioma-portugues.md)) e seguem as convenções do [dicionário de dados](../dados/dicionario-de-dados.md); os contratos dos eventos de origem estão em [contracts/](../../contracts/README.md).
