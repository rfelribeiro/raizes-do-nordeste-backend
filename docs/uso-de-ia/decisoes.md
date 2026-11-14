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
| D-017 | 2026-11-02 | **Visão analítica como identidade do projeto:** modelagem de dados pensada para análise moderna, com entrega de um Data Warehouse que tenha margem para evoluir para Lakehouse. Justificativa do autor: a rede não é uma empresa de tecnologia, mas dados são essenciais para qualquer empresa | 🧑 Humana | Visão pessoal do autor como arquiteto, sem desviar do escopo da API. ADR-0007 |
| D-018 | 2026-11-02 | Motor e armazenamento analíticos: **DuckDB + Parquet** (bronze em Parquet particionado; caminho Lakehouse com object storage, Iceberg e Trino/Spark) | 🤝 Conjunta | Recomendação da IA aceita. ADR-0008 |
| D-019 | 2026-11-02 | Captura OLTP → analítico: **Outbox de eventos de domínio** (CDC com Debezium fica como evolução conceitual) | 🤝 Conjunta | Recomendação da IA aceita. A outbox também atende à auditoria. ADR-0008 |
| D-020 | 2026-11-02 | Modelagem da camada de consumo (gold): **Kimball, esquema estrela** | 🤝 Conjunta | Recomendação da IA aceita. ADR-0008 |
| D-021 | 2026-11-02 | Transformações bronze → silver → gold com **dbt-core** | 🤝 Conjunta | Recomendação da IA aceita. ADR-0008 |
| D-022 | 2026-11-02 | A matriz de barramento (processos × dimensões), os grãos das fatos e as estratégias de SCD ficam para o **humano desenhar** (superada por D-028 a D-032). A IA entrega só o modelo do documento e os insumos extraídos do estudo de caso | 🤖 IA | Proposta para preservar a autoria do humano na área de especialidade dele, **aguardando validação** |
| D-023 | 2026-11-02 | Objetos de banco (tabelas, colunas, modelos dbt) em português `snake_case`; código Python em inglês | 🤖 IA | Mantém a linguagem do negócio para os analistas da rede. **Aguardando validação**. ADR-0008 |
| D-024 | 2026-11-02 | O bronze é particionado pela **data de captura** (`registrado_em`, UTC), e não pela data de ocorrência do evento | 🤖 IA | O subagente decidiu. Mantém o bronze append-only e a reprocessabilidade. **Aguardando validação** |
| D-025 | 2026-11-02 | A extração da outbox ignora eventos com menos de 5 s (`DW_EXTRACAO_DEFASAGEM_SEGUNDOS`), para não perder transações confirmadas fora de ordem | 🤖 IA | O subagente decidiu. O risco residual de transações longas está registrado no ADR-0008. **Aguardando validação** |
| D-026 | 2026-11-02 | `dim_tempo`: feriados nacionais 2024–2030, incluindo Carnaval (ponto facultativo) e Consciência Negra; período junino parametrizado com padrão de 01/06 a 31/07 | 🤖 IA | O subagente decidiu. **O período junino é regra de negócio a ser validada pelo autor** |
| D-027 | 2026-11-02 | Bronze vazio: o extrator cria um Parquet de esquema com 0 linhas (`dt=1970-01-01`), para que o dbt rode sem dados | 🤖 IA | O subagente decidiu, por questão técnica. Documentado em `analytics/README.md` |
| D-028 | 2026-11-14 | Matriz de barramento: 9 processos (itens de pedido, pedidos, ciclo de vida do pedido, pagamentos, movimentação e saldo de estoque, fidelidade, operações sensíveis, consentimentos), dimensões, grãos e interseções linha a linha | 🧑 Humana | Sessão guiada: a IA apresentou as opções e o conceito de cada uma; o humano escolheu item a item. `docs/dados/matriz-de-barramento.md` |
| D-029 | 2026-11-14 | Dimensão Cliente pseudonimizada, número do pedido como dimensão degenerada, `dim_tempo` role-playing no ciclo de vida, membro -1 para cliente não identificado | 🤝 Conjunta | A IA apontou a inconsistência (Fidelidade e Consentimentos sem a dimensão Cliente); o humano escolheu a solução |
| D-030 | 2026-11-14 | Nova `dim_finalidade` (com a base legal LGPD) e Canal no fato de consentimentos | 🤖 IA | Exigida pelo grão "cliente × finalidade × dia" escolhido pelo humano. Definida pela IA a pedido do humano ("defina de acordo com boas práticas de mercado") |
| D-031 | 2026-11-14 | Estratégia de SCD por atributo (tipo 2 em formato da unidade, categoria/sazonalidade do produto, perfil do cliente e papel/lotação do colaborador; tipo 1 nas listas de referência; tipo 0 em tempo e hora), membros especiais -1 e -2 (anonimizado, LGPD), FKs nunca nulas | 🤖 IA | Definida pela IA a pedido do humano, seguindo as boas práticas de Kimball |
| D-032 | 2026-11-14 | Medidas e aditividade de cada fato; sazonalidade como atributo do produto (SCD 2) e da data (`eh_periodo_junino`), com recomendação de um calendário comercial governado pelo negócio | 🤖 IA | Definida pela IA a pedido do humano. O período junino continua provisório (D-026) |
