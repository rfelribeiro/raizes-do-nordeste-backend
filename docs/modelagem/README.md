# Modelagem

Espaço reservado para a modelagem do sistema (seção 4 do documento principal): casos de uso,
diagrama de classes, DER (modelo de dados) e diagramas de sequência e de estado (ex.: ciclo de
vida do pedido).

_Conteúdo a ser produzido._

## Dois modelos, dois propósitos

- **DER do OLTP:** modelo relacional normalizado do banco transacional (PostgreSQL) que a API usa.
  Aqui entra o DER descrito acima.
- **Modelo dimensional do DW:** esquema estrela (Kimball) da camada analítica, no DuckDB. É um
  modelo à parte, derivado dos eventos de domínio, e é de **autoria humana**: matriz de
  barramento, grãos, fatos, dimensões e SCD ficam em
  [docs/dados/matriz-de-barramento.md](../dados/matriz-de-barramento.md). Os nomes técnicos dos objetos estão em inglês e seguem as convenções do [dicionário de dados](../dados/dicionario-de-dados.md) (ADR 0009); os contratos dos eventos de origem estão em [contracts/](../../contracts/README.md).
