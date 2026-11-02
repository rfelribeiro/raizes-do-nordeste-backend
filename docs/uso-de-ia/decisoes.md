# Log de decisões: humano × IA

Origem: 🧑 Humana · 🤝 Conjunta (a IA propôs, o humano escolheu) · 🤖 IA (pendente de validação humana). Veja a legenda completa em [README.md](README.md#legenda-de-origem).
As decisões de arquitetura têm um ADR correspondente em [`docs/arquitetura/adr/`](../arquitetura/adr/).

| ID | Data | Decisão | Origem | Observações e evidência |
|---|---|---|---|---|
| D-000 | 2026-11-02 | Converter o PDF do roteiro em Markdown (`init/roteiro.md`) usando agentes de menor custo e um agente revisor | 🧑 Humana | Sessão `4b866578` |
| D-001 | 2026-11-02 | Trilha **Back-end**, com foco em uma API funcional que atenda ao roteiro | 🧑 Humana | Sessão `62e92532`, primeiro prompt |
| D-002 | 2026-11-02 | Trabalhar com o Claude Code como par de arquitetura (Opus 5.5) e delegar o trabalho braçal a modelos de menor custo (Sonnet e Haiku 5.5) | 🧑 Humana | Motivo: cota limitada do plano Pro |
| D-003 | 2026-11-02 | Registrar todo o processo, separando decisão humana de decisão da IA, como forma de cumprir a exigência de declarar o uso de IA | 🧑 Humana | Interpretação do autor sobre a seção "Uso de IA" do roteiro |
| D-004 | 2026-11-02 | Repositório git local restrito à pasta `raizes/` | 🧑 Humana | Mensagem enviada durante o turno |
| D-005 | 2026-11-02 | Commits com o login do GitHub e o e-mail *noreply*, configurados só neste repositório | 🤝 Conjunta | A IA alertou que o e-mail global era pessoal; o humano escolheu o noreply |
| D-006 | 2026-11-02 | Linguagem e framework: **Python + FastAPI** | 🤝 Conjunta | Recomendação da IA aceita. ADR-0001 |
| D-007 | 2026-11-02 | Arquitetura em **camadas: API, Aplicação, Domínio e Infraestrutura** | 🧑 Humana | A IA recomendou "monólito modular"; o humano optou por camadas explícitas. ADR-0002 |
| D-008 | 2026-11-02 | Dentro de cada camada, um subpacote por módulo de negócio | 🤖 IA | Proposta complementar à D-007, **aguardando validação**. ADR-0002 |
| D-009 | 2026-11-02 | Banco de dados **PostgreSQL** | 🤝 Conjunta | Recomendação da IA aceita. ADR-0003 |
| D-010 | 2026-11-02 | Requisito: o examinador precisa conseguir reproduzir com fidelidade o que roda localmente | 🧑 Humana | Mensagem enviada durante o turno |
| D-011 | 2026-11-02 | Solução para a D-010: Docker Compose como ambiente canônico, versões travadas (imagens e lockfiles), Makefile, `.env` gerado localmente e CI | 🤖 IA | ADR-0004 |
| D-012 | 2026-11-02 | Requisito: de maneira nenhuma expor credenciais ou dados sensíveis | 🧑 Humana | Mensagem enviada durante o turno |
| D-013 | 2026-11-02 | Solução para a D-012: `.env` fora do git, `.env.example` só com valores fictícios, senha local aleatória, verificação de segredos no pre-commit e na CI, redação dos registros de IA | 🤖 IA | ADR-0005 |
| D-014 | 2026-11-02 | Mecanismo de registro: exportação automática das conversas pelos hooks `Stop` e `SubagentStop`, com redação de dados pessoais | 🤖 IA | Atende à D-003. ADR-0006 |
| D-015 | 2026-11-02 | Os registros de conversa não incluem o raciocínio interno do modelo nem as saídas de ferramentas, só prompts, respostas, comandos, arquivos tocados e decisões | 🤖 IA | Motivos: privacidade (as saídas podem conter dados da máquina) e legibilidade |
| D-016 | 2026-11-02 | Python 3.14 no container (a mesma versão da máquina local) e PostgreSQL 17 | 🤖 IA | Detalhe de versão. ADR-0001 e ADR-0003 |
