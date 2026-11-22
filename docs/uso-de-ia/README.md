# Registro do uso de IA

O roteiro da disciplina exige que, se houver uso de IA em qualquer etapa, o trabalho declare **a ferramenta utilizada, os prompts e os trechos aproveitados**, com evidências do processo. Esta pasta reúne essa declaração e as evidências, para que qualquer pessoa consiga separar o que foi **decisão humana** do que foi **proposta ou produção da IA**.

## Como o trabalho é dividido

| Papel | Quem | Responsabilidade |
|---|---|---|
| Arquiteto e decisor | Humano (autor do projeto) | Define requisitos, escolhe a stack e a arquitetura, aprova ou rejeita propostas e revisa os artefatos |
| Par de arquitetura | Claude Opus 5.5 (sessão principal do Claude Code) | Explica conceitos, apresenta opções com prós e contras, especifica tarefas para os subagentes e revisa o resultado deles |
| Trabalho braçal | Subagentes Claude Sonnet 5.5 e Claude Haiku 5.5 | Executam tarefas mecânicas sob especificação escrita (coleta de dados, scaffolding, scripts) |

O ambiente e as versões das ferramentas estão em [01-infraestrutura.md](01-infraestrutura.md).

## O que existe aqui

| Arquivo | Conteúdo | Como é mantido |
|---|---|---|
| [01-infraestrutura.md](01-infraestrutura.md) | Máquina, sistema operacional, IDE, plano e modelos de IA | Coletado por subagente e revisado pelo humano |
| [decisoes.md](decisoes.md) | Log de decisões com a origem de cada uma (humana, IA ou conjunta) | Manual, a cada decisão relevante |
| [conversas/](conversas/README.md) | Transcrição de todas as conversas com a IA, com os subagentes e os prompts enviados a eles | **Automático**, por hook do Claude Code |

## Exportação automática das conversas

- Ao final de cada resposta da IA (eventos `Stop` e `SubagentStop`), o hook em [`.claude/settings.json`](../../.claude/settings.json) roda [`tools/registro_ia/exportar_conversas.py`](../../tools/registro_ia/README.md), que regenera o Markdown da sessão em `conversas/`.
- **O que entra:** prompts humanos (inclusive mensagens enviadas no meio de um turno), respostas da IA, chamadas de ferramenta (comandos executados e arquivos tocados), prompts completos enviados aos subagentes e as perguntas que a IA fez ao humano junto com as respostas (marcadas como 🧭 *Decisão humana*).
- **O que não entra:** raciocínio interno do modelo, saídas de ferramentas e conteúdo dos arquivos criados (esse conteúdo está no próprio histórico do git), além do contexto injetado automaticamente pelo sistema ou pela IDE.
- **Privacidade:** e-mails, usuário do SO, hostname, caminhos pessoais, IPs e padrões de token são redigidos automaticamente. Termos pessoais adicionais ficam no arquivo local `.registro-ia.local`, que está no `.gitignore` e nunca é versionado. Antes de cada commit, um hook de pre-commit procura segredos e termos privados nos arquivos.

## Legenda de origem

| Marca | Significado |
|---|---|
| 🧑 Humana | O humano definiu sem proposta prévia da IA, ou escolheu algo diferente do que a IA recomendou |
| 🤝 Conjunta | A IA apresentou opções ou recomendou e o humano escolheu ou aprovou explicitamente |
| 🤖 IA | A IA decidiu um detalhe de implementação dentro do escopo delegado. Fica **pendente de validação humana** até ser marcada como revisada |

## Inventário de artefatos produzidos com IA ("trechos aproveitados")

Atualize a coluna **Revisão humana** à medida que revisar cada item.

| Artefato | Produzido por | Especificado por | Revisão humana |
|---|---|---|---|
| `init/roteiro.md` (transcrição do PDF do roteiro; mantida só localmente, não publicada, D-055) | Subagentes, com revisor | Humano | ⏳ pendente |
| `docs/uso-de-ia/01-infraestrutura.md` | Subagente Haiku 5.5 | Opus 5.5 | ⏳ pendente |
| `tools/registro_ia/` (exportador e testes) | Subagente Sonnet 5.5, com ajuste do Opus 5.5 | Opus 5.5, a pedido do humano | ⏳ pendente |
| `.claude/settings.json`, `.gitignore`, este README, `decisoes.md` | Opus 5.5 | Humano | ⏳ pendente |
| Estrutura inicial da API, docs de arquitetura, ADRs 0001–0006, verificador de segredos e CI | Subagente Sonnet 5.5, revisado pelo Opus 5.5 | Opus 5.5, com as decisões do humano | ⏳ pendente |
| Fundação analítica: outbox, `analytics/`, dbt, `docs/dados/`, ADRs 0007–0008 | Subagente Sonnet 5.5 | Opus 5.5, com as decisões do humano (D-017 a D-021) | ⏳ pendente |
| `docs/dados/matriz-de-barramento.md`: só a estrutura e os insumos; o **conteúdo é do humano** | Subagente Sonnet 5.5 (estrutura) | Humano (D-022) | ✅ preenchida: escolhas do humano (D-028, D-029) e boas práticas definidas pela IA a pedido dele (D-030 a D-032) |
| Renomeação para inglês, `docs/dados/dicionario-de-dados.md`, `contracts/` (envelope JSON Schema + contrato ODCS), contratos dbt, ADR-0009 | Subagente Sonnet 5.5, revisado pelo Opus 5.5 | Humano (D-033); mapa de nomes e convenções pelo Opus 5.5 | ⏳ pendente |
| `docs/requisitos/README.md` (RF/RNF com MoSCoW, regras de negócio, LGPD, pagamento mock, priorização) | Subagente Sonnet 5.5, revisado pelo Opus 5.5 | Escopo pelo humano (D-038 a D-045); detalhes pela IA a pedido dele (D-046) | ⏳ pendente |
| `docs/modelagem/der.md` (DER do OLTP: diagramas, dicionário físico, conceitos, rastreabilidade) | Subagente Sonnet 5.5, revisado pelo Opus 5.5 | Estrutura pelo humano (D-047 a D-049); tipos e constraints pela IA (D-051, D-052) | ⏳ pendente |
| `docs/entrega/` (esqueleto do documento principal, seção a seção com exigências do roteiro) | Opus 5.5 | Humano (D-053) | ⏳ pendente |
| `docs/modelagem/` (casos de uso, classes, sequência) | Subagente Sonnet 5.5, revisado pelo Opus 5.5 | Opus 5.5, com as decisões do humano (D-050, D-054) | ⏳ pendente |
| Implementação do fluxo A: migração, domínio, segurança, casos de uso, rotas, gateway mock, testes (`src/`, `migrations/`, `tests/`, `scripts/seed.py`) | Subagentes Sonnet 5.5 em worktrees paralelas, revisados e integrados pelo Opus 5.5 | Opus 5.5 (`docs/implementacao/plano-mvp.md`), com o recorte do humano (D-057) | ⏳ pendente |
| Coleção Postman (`postman/`), plano de testes e evidências (`docs/testes/`) | Subagente Sonnet 5.5, revisado pelo Opus 5.5 | Opus 5.5, a partir do roteiro | ⏳ pendente |
| `docs/api/` e seções 3.1, 3.4, 3.5, 4.3, 6.3, 6.4 e 7 deste documento | Subagentes Sonnet 5.5 e Haiku 5.5, revisados pelo Opus 5.5 | Opus 5.5 | ⏳ pendente |
