---
titulo: "Rede Raízes do Nordeste: API Back-end multicanal"
subtitulo: "Projeto Multidisciplinar — Trilha Back-end"
# Os dados da capa (nome, RU, polo, semestre, professor) NÃO ficam neste arquivo.
# Eles são lidos de docs/entrega/capa.local.yaml (fora do git) na geração do .docx/.pdf.
---

<!--
ESQUELETO DO DOCUMENTO PRINCIPAL (fonte em Markdown → .docx → PDF único)

Estrutura = "Documento principal" do roteiro geral (init/roteiro.md) + seções obrigatórias
do roteiro da trilha (init/roteiro_trilha_backend.md). Cada seção traz:
  - EXIGE: o que o roteiro pede (com a linha);
  - FONTE: o artefato do repositório que alimenta a seção;
  - STATUS: ⬜ a escrever · ✏️ rascunho · ✅ revisado pelo autor;
  - AUTORIA: quem redige o texto final (🧑 autor · 🤖 rascunho da IA revisado pelo autor).
Os comentários HTML não saem no documento final.
-->

# Capa e folha de rosto

<!--
EXIGE: curso, disciplina, nome, RU, polo de apoio, semestre e professor (roteiro geral, "Capa e Sumário").
FONTE: docs/entrega/capa.local.yaml (privado). STATUS: ⬜ AUTORIA: 🧑
Nome do arquivo final: <RU>_Projeto_Back_End.PDF (trilha L418).
-->

# Sumário

<!-- Gerado automaticamente na conversão. -->

# 1 Introdução e objetivos

<!--
EXIGE: contexto do estudo de caso, objetivos do projeto, principais usuários e relevância do sistema
(roteiro geral); foco no negócio e numa API que suporte múltiplos canais (trilha L71–L75).
FONTE: docs/requisitos/README.md §1 e §2; init/roteiro.md (estudo de caso).
STATUS: ⬜ AUTORIA: 🧑 (texto autoral, recomendado escrever com a própria voz)
-->

## 1.1 Contexto

## 1.2 Objetivos do projeto

## 1.3 Principais usuários

## 1.4 Relevância e visão do autor

<!-- Espaço para a visão analítica (D-017): dados como ativo de uma rede que não é empresa de tecnologia. -->

# 2 Análise e requisitos

<!--
EXIGE: RF e RNF de back-end com foco em regras, persistência, integrações e segurança (trilha L89–L120);
multicanalidade com canalPedido (L104–L114); priorização implementado × proposto com justificativa (L447, L545).
FONTE: docs/requisitos/README.md (RF-01..RF-22, RNF-01..RNF-15, RN-01..RN-13).
STATUS: ⬜ AUTORIA: 🤖 → 🧑
-->

## 2.1 Atores e perfis de acesso

## 2.2 Requisitos funcionais

## 2.3 Requisitos não funcionais

## 2.4 Regras de negócio

## 2.5 Multicanalidade

## 2.6 Priorização do MVP (MoSCoW) e trade-offs

# 3 Modelagem e arquitetura

<!--
EXIGE: casos de uso, DER, arquitetura em camadas, diagrama de classes; sequência/atividade recomendado
(trilha L122–L160). DER compatível com o banco usado na API (L288–L290).
FONTE: docs/modelagem/ (der.md pronto; casos de uso, classes, sequência e estados a produzir);
docs/arquitetura/visao-geral.md e ADRs.
STATUS: ⬜
-->

## 3.1 Diagrama e descrição dos casos de uso

<!-- Seguir o modelo de descrição do anexo do roteiro (trilha L564). -->

## 3.2 Modelo de dados (DER)

## 3.3 Arquitetura em camadas

## 3.4 Diagrama de classes do domínio

## 3.5 Diagrama de sequência: pedido → pagamento → status

## 3.6 Diagrama de estados do pedido

## 3.7 Tecnologias e persistência

# 4 API e endpoints

<!--
EXIGE: organização por recurso (trilha L176), checklist por endpoint (L194), regras mínimas (L209),
campos e padrões do contrato com canalPedido e erro padronizado (L220–L248); usar o template do anexo (L628).
FONTE: docs/api/ (a produzir) + OpenAPI gerado pela API.
STATUS: ⬜
-->

## 4.1 Organização por recurso

## 4.2 Padrões do contrato (paginação, filtros, erro padrão)

## 4.3 Endpoints do fluxo crítico

# 5 LGPD, privacidade e segurança no back-end

<!--
EXIGE: dados coletados, finalidade, base legal, registro do consentimento; hash de senha, token,
autorização por perfil, logs de acesso a dados sensíveis, retenção/anonimização (trilha L252).
FONTE: docs/requisitos/README.md §7; RNF-01..RNF-07.
STATUS: ⬜
-->

## 5.1 Inventário de dados pessoais

## 5.2 Consentimento

## 5.3 Autenticação, autorização e proteção das respostas

## 5.4 Logs e trilha de auditoria

## 5.5 Retenção, anonimização e pseudonimização analítica

# 6 Entrega técnica

<!--
EXIGE: repositório público com histórico de commits, README reprodutível, OpenAPI/Swagger,
coleção Postman, DER compatível com o banco (trilha L258–L290); MVP mínimo (L291–L313); evidências (L315–L330).
FONTE: README.md, docker-compose, migrations, /docs da API, git log.
STATUS: ⬜ (depende da implementação)
-->

## 6.1 Repositório e organização do código

## 6.2 Como executar (resumo do README)

## 6.3 Fluxo crítico entregue

## 6.4 Evidências de funcionamento

# 7 Plano de testes e evidências

<!--
EXIGE: ≥10 cenários (mín. 6 positivos e 4 negativos) com entrada e saída esperada (trilha L345);
coberturas obrigatórias (L363); formato recomendado (L399); evidência executável (L336).
FONTE: docs/testes/ (a produzir), coleção Postman, testes automatizados, relatório k6.
STATUS: ⬜ (depende da implementação)
-->

## 7.1 Estratégia de validação

## 7.2 Cenários de teste

## 7.3 Evidências de execução

## 7.4 Teste de carga (desempenho no pico)

# 8 Conclusão

<!--
EXIGE (trilha L420–L422): o que foi implementado e o que ficou como proposta, com as prioridades;
como DER/Classes/Casos de Uso se conectam aos endpoints e ao fluxo crítico; como o pagamento mock
foi tratado; validações e erros padronizados; cuidados de segurança/LGPD; como os testes evidenciam
o funcionamento. Roteiro geral: lições aprendidas, desafios e evoluções futuras.
Ponte para a proposta final à Raízes (D-037): construir × comprar.
STATUS: ⬜ AUTORIA: 🧑 (texto autoral)
-->

# Referências

<!-- ABNT NBR 6023. Registrar só o que foi efetivamente usado. -->

# Apêndice A — Declaração de uso de inteligência artificial

<!--
EXIGE (trilha L81): ferramenta utilizada, prompts e trechos aproveitados, no final do documento.
FONTE: docs/uso-de-ia/ (README, 01-infraestrutura.md, decisoes.md, conversas/).
STATUS: ⬜ AUTORIA: 🤖 → 🧑
-->

# Apêndice B — Visão analítica: do banco transacional ao Data Warehouse

<!--
Diferencial do autor (D-017; não pontua diretamente, D-036). Outbox, medallion, Kimball, matriz de barramento.
FONTE: docs/dados/, analytics/, ADRs 0007–0008.
STATUS: ⬜ AUTORIA: 🧑 (modelagem dimensional é autoria do humano)
-->

# Apêndice C — Diagramas complementares

<!-- Diagramas UML extras (componentes, implantação), se necessários (roteiro geral, "Materiais suplementares"). -->
