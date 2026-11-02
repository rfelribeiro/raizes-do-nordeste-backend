# ADR 0002 - Arquitetura em camadas: API, Aplicação, Domínio, Infraestrutura

- **Status:** aceita (camadas); proposta — aguardando validação humana (subdivisão por módulo)
- **Data:** 2026-11-02

## Contexto

O estudo de caso descreve múltiplos módulos (pedidos, estoque, pagamentos, fidelidade, auditoria, relatórios) e exige rastreabilidade e manutenção em crescimento acelerado. Era preciso definir o estilo arquitetural.

## Decisão

Aplicação única implantável organizada em **quatro camadas explícitas**: API, Aplicação, Domínio e Infraestrutura.

Regra de dependência: api → application → domain; infrastructure → application e domain (implementa portas); domain não depende de ninguém. A regra é verificada automaticamente em `tests/architecture`.

**Proposta da IA (aguardando validação humana):** dentro de cada camada, um subpacote por módulo de negócio (ex.: `domain/pedidos`, `application/pedidos`, `api/v1/pedidos.py`), para manter fronteiras de domínio e permitir extração futura.

## Alternativas consideradas

- **Monólito modular** (recomendação inicial da IA): módulos como unidade primária de organização, cada um com suas camadas internas.
- Microsserviços: complexidade operacional desproporcional ao escopo acadêmico.

## Consequências

- (+) Separação clara de responsabilidades; domínio testável sem framework nem banco.
- (+) Regra de dependência verificável automaticamente.
- (-) Mais arquivos e indireção que uma estrutura plana.
- (-) Sem disciplina, módulos de negócio podem se acoplar entre si; a subdivisão por módulo proposta mitiga isso, mas ainda não foi validada.

**Autoria da decisão:** **humana.** A IA havia recomendado "monólito modular"; o humano optou por camadas explícitas. A subdivisão por módulo dentro das camadas é proposta da IA, ainda sem validação humana.
