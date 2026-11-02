# ADR 0003 - Banco de dados: PostgreSQL 17

- **Status:** aceita
- **Data:** 2026-11-02

## Contexto

O sistema trata pedidos, estoque e pagamentos (consistência forte), tem picos de concorrência, variações regionais de cardápio e relatórios analíticos para a matriz.

## Decisão

Usar **PostgreSQL 17** (imagem `postgres:17.11-alpine`), acessado via SQLAlchemy 2 (driver psycopg 3) com migrações Alembic.

Motivos: transações ACID para pedidos/estoque/pagamentos; bom comportamento sob concorrência (MVCC, bloqueios por linha) em horário de pico; JSONB para variações regionais; SQL analítico (janelas, agregações) para relatórios.

## Alternativas consideradas

- MySQL/MariaDB
- SQL Server
- Bancos NoSQL de documentos

## Consequências

- (+) Integridade transacional e recursos analíticos no mesmo banco.
- (-) Escala de escrita vertical por padrão; réplicas de leitura podem ser necessárias para relatórios.

**Autoria da decisão:** **humana.** Era a opção recomendada pela IA.
