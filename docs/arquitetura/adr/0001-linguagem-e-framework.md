# ADR 0001 - Linguagem e framework: Python 3.14 + FastAPI

- **Status:** aceita
- **Data:** 2026-11-02

## Contexto

O projeto exige uma API back-end com documentação clara para avaliação, validação de entrada e integração com banco relacional. Era preciso escolher linguagem e framework.

## Decisão

Usar **Python 3.14** com **FastAPI**, SQLAlchemy 2 e Alembic, testes com pytest.

Motivos: o autor tem base em Python e dados; o OpenAPI é gerado automaticamente (Swagger em `/docs`), o que facilita a avaliação; a validação é feita com Pydantic; o ecossistema SQLAlchemy/Alembic/pytest é maduro.

## Alternativas consideradas

- Java com Spring Boot
- TypeScript com NestJS
- C# com ASP.NET Core

## Consequências

- (+) Desenvolvimento rápido e documentação de API automática.
- (+) Tipagem estática opcional verificada com mypy.
- (-) Desempenho bruto menor que plataformas compiladas; mitigável com escala horizontal.
- (-) Python 3.14 é recente: dependências são travadas em lockfile (ver ADR 0004).

**Autoria da decisão:** **humana.** Era a opção recomendada pela IA; o humano a escolheu.
