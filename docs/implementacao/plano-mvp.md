# Plano de implementação do MVP

Especificação usada para orquestrar os agentes de implementação (D-057, D-058). Quem implementa um
pedaço lê **este arquivo inteiro** antes de começar e segue as convenções da seção 4.

## 1. Escopo: o mínimo do roteiro

O objetivo do trabalho **não** é um back-end completo. O diferencial é a análise
(construir × comprar, [proposta final](../proposta/README.md)). Implementa-se só a **fatia
vertical que o roteiro exige** (RT p. 5 e p. 8): o fluxo A, pedido → pagamento mock aprovado ou
recusado → status, com persistência real, JWT, regra de perfil, 409 de estoque, `canalPedido`
filtrável, erro padrão, auditoria e coleção Postman. O restante fica **modelado e documentado**
(requisitos, DER, casos de uso), sem código.

| Requisito | Situação | Observação |
|---|---|---|
| RF-02 Login com JWT | **Implementar** | Usuários de demonstração vêm da carga inicial (`make seed`) |
| RF-03 Autorização por perfil e unidade | **Implementar** | 401, 403 e 404 do RNF-03 |
| RF-07 Criar pedido | **Implementar** | `canalPedido`, RN-12, RN-14, reserva com bloqueio, 409 `ESTOQUE_INSUFICIENTE`; **sem** `Idempotency-Key` e **sem** resgate de pontos |
| RF-08 Listar e consultar pedidos | **Implementar** | Filtros `canalPedido`, `status`, `unidadeId`; paginação |
| RF-09 Atualizar status | **Implementar** | Máquina de estados (RN-03) e quem faz cada transição (RN-04); só `EM_PREPARO`, `PRONTO`, `ENTREGUE` |
| RF-11 e RF-12 Pagamento mock | **Implementar** | Serviço HTTP separado (D-041); `tok_aprovado`, `tok_recusado`, `tok_timeout`; timeout 3 s com 2 novas chamadas; 504 ao esgotar; **sem** idempotência |
| RF-13 Auditoria | **Implementar** | Gravação nas ações do fluxo e `GET /auditoria` |
| RF-14 Consentimento | **Implementar (mínimo)** | Registrar, revogar e listar os próprios consentimentos (LGPD) |
| RF-22 Outbox | **Implementar** | `pedido_criado`, `pagamento_aprovado`, `pagamento_recusado`, `status_pedido_alterado`: alimenta o DW |
| RF-01, RF-04 a RF-06, RF-10, RF-15 a RF-18 | Modelado, não implementado | Dados de unidades, catálogo, cardápio e estoque entram pela carga inicial |
| RF-19 a RF-21 | Conceitual | Já eram só documentados |

RNF no código: RNF-01 (Argon2id), RNF-02 (JWT 60 min), RNF-03, RNF-05, RNF-06 (já existe),
RNF-09 (já existe), RNF-10 (sem idempotência), RNF-11, RNF-12, RNF-13 (já existe), RNF-14,
RNF-15. O RNF-08 (k6) fica documentado, sem medição.

**Tabelas da migração `0002`** (subconjunto do [DER](../modelagem/der.md), colunas e CHECKs
idênticos ao dicionário físico): `unidades`, `usuarios`, `categorias`, `produtos`,
`itens_cardapio`, `estoques`, `movimentacoes_estoque`, `pedidos`, `itens_pedido`,
`historico_status_pedido`, `tentativas_pagamento`, `consentimentos`, `auditoria`. Ficam fora:
`saldos_pontos`, `movimentos_pontos`, `chaves_idempotencia`. A `outbox_eventos` já existe.

Fontes normativas, nesta ordem: [requisitos](../requisitos/README.md), [DER](../modelagem/der.md),
[casos de uso](../modelagem/casos-de-uso.md) (UC-02, UC-04, UC-05, UC-06, UC-09, UC-11),
[classes](../modelagem/classes.md), [sequência](../modelagem/sequencia.md),
[API](../api/README.md). Na dúvida, não implemente: registre no relatório final.

## 2. Contrato HTTP (todas as rotas sob `/api/v1`)

| Método e rota | Quem | Sucesso | Erros principais |
|---|---|---|---|
| `POST /auth/login` `{email, senha}` | público | 200 `{accessToken, tokenType: "bearer", expiresIn: 3600}` | 401 credenciais inválidas, 422 |
| `POST /pedidos` `{unidadeId, canalPedido, clienteId?, itens: [{produtoId, quantidade}]}` | CLIENTE (APP, WEB, PICKUP); ATENDENTE e GERENTE da unidade (BALCAO, TOTEM) | 201 pedido | 401, 403, 404, 409 `ESTOQUE_INSUFICIENTE`, 422 (`canalPedido` ausente, inválido ou incompatível com o perfil) |
| `GET /pedidos?canalPedido&status&unidadeId&page&limit` | CLIENTE (só os seus), colaborador (só a sua unidade), ADMIN (todos) | 200 `{items, page, limit, total}` | 401, 422 |
| `GET /pedidos/{id}` | idem | 200 pedido com itens | 401, 403 (colaborador de outra unidade), 404 (inexistente ou de outro cliente) |
| `PATCH /pedidos/{id}/status` `{status, motivo?}` | COZINHA, ATENDENTE, GERENTE (RN-04) | 200 pedido | 401, 403, 404, 409 `TRANSICAO_INVALIDA`, 422 |
| `POST /pedidos/{id}/pagamentos` `{formaPagamento, tokenPagamento}` | CLIENTE dono do pedido | 201 `{tentativa, statusPedido}` (aprovado: PAGO; recusado: `status` RECUSADO e motivo) | 401, 403, 404, 409 (pedido fora de AGUARDANDO_PAGAMENTO), 422, 504 (timeout esgotado) |
| `POST /consentimentos` `{finalidade, acao, versaoTermo}` | CLIENTE | 201 | 401, 403, 422 |
| `GET /consentimentos` | CLIENTE (os seus, com o vigente por finalidade) | 200 | 401, 403 |
| `GET /auditoria?acao&tipoRecurso&page&limit` | ADMIN (tudo), GERENTE (sua unidade) | 200 paginado | 401, 403 |

Pedido na resposta: `id`, `numeroPedido`, `unidadeId`, `clienteId`, `canalPedido`, `status`,
`itens [{produtoId, quantidade, precoUnitario, valorTotalItem}]`, `valorItens`, `valorDesconto`,
`valorTotal`, `expiraEm`, `criadoEm`. Valores monetários como string decimal com 2 casas.

Efeitos no estoque: criação = `RESERVA` (disponível → reservado); pagamento aprovado = `BAIXA`
(reservado sai). Recusa mantém a reserva (UC-05).

## 3. Ondas e responsáveis

Cada pedaço roda num agente com **worktree git própria**. A sessão principal (Opus) revisa,
integra no `main` e roda a verificação completa entre as ondas.

| Onda | Pedaço | Modelo | Entrega |
|---|---|---|---|
| 1 | **A. Esquema e carga** | Sonnet | Migração `0002` (tabelas da seção 1), modelos ORM, `make seed` |
| 1 | **B. Plataforma e login** | Sonnet | Argon2id, JWT, `Principal` do token, exigência de perfil, unidade de trabalho, composição, paginação, erros 401/403/409/422/504, `POST /auth/login` |
| 1 | **C. Domínio e gateway mock** | Sonnet | Agregados `Order` e `Stock`, máquina de estados, políticas RN-04 e RN-14, portas; serviço `gateway-mock` no compose |
| 1 | **D. Documentação do escopo** | Haiku | Coluna "Entrega" dos requisitos e menções no documento principal |
| 2 | **E. Fluxo A** | Sonnet | Repositórios, casos de uso, rotas de pedidos, pagamento, consentimento e auditoria; testes de integração |
| 2 | **F. Coleção Postman** | Sonnet | ≥ 10 cenários (6 positivos, 4 negativos), ambiente, `make postman` com newman em contêiner |
| 3 | **Revisão** | Opus | Revisão, integração, `docs/api`, seções 4.3, 6.3, 6.4 e 7 do documento |

Fronteiras de arquivos na onda 1 (para não haver conflito):

- **A** é dono de `migrations/versions/*0002*`, `src/raizes/infrastructure/db/models/` (exceto
  `outbox.py`) e `scripts/seed.py`.
- **B** é dono de `src/raizes/infrastructure/security/`, `src/raizes/api/composition/`,
  `src/raizes/api/security.py`, `src/raizes/api/pagination.py`, `src/raizes/application/errors.py`,
  `src/raizes/api/errors.py`, `src/raizes/application/ports/{unit_of_work,security,users}.py`,
  `src/raizes/application/identity/`, `src/raizes/api/v1/auth.py`, `src/raizes/main.py`,
  `src/raizes/api/v1/router.py`, `tests/architecture/`, `tests/integration/conftest.py`.
- **C** é dono de `src/raizes/domain/{orders,stock}/`,
  `src/raizes/application/ports/{orders,stock,payment_gateway,audit,consent}.py`,
  `services/gateway_mock/` e do serviço `gateway-mock` no `docker-compose.yml`.

## 4. Convenções obrigatórias

### 4.1 Contratos já escritos (não altere sem combinar)

- [`domain/shared/enums.py`](../../src/raizes/domain/shared/enums.py): `Role`, `OrderChannel`,
  `OrderStatus`, `StockMovementType`, `PointsMovementType`, `PaymentMethod`,
  `PaymentAttemptStatus`, `ConsentPurpose`, `ConsentAction`, `UnitFormat`.
- [`application/principal.py`](../../src/raizes/application/principal.py): `Principal(user_id, role, unit_id)`.

### 4.2 Organização

Identificadores do código em **inglês** (ADR 0010, item 3; mapa em
[classes.md §5](../modelagem/classes.md#5-mapeamento-classe-de-domínio-e-der)); rotas, campos JSON,
mensagens, valores de enum, tabelas e colunas em **português**.

| Camada | Caminho | Observação |
|---|---|---|
| Domínio | `src/raizes/domain/<modulo>/` | Só biblioteca padrão; sem I/O |
| Aplicação | `src/raizes/application/<modulo>/` e `src/raizes/application/ports/<porta>.py` | Sem FastAPI e sem SQLAlchemy |
| API | `src/raizes/api/v1/<modulo>.py` e `src/raizes/api/schemas/<modulo>.py` | Não importa `raizes.infrastructure.db` |
| Composição | `src/raizes/api/composition/<modulo>.py` | Único lugar da API que importa a infraestrutura |
| Infraestrutura | `src/raizes/infrastructure/db/{models,repositories}/<modulo>.py`, `.../security/`, `.../payment/` | Implementa as portas |
| Testes | `tests/unit/<modulo>/`, `tests/integration/<modulo>/` | Integração com `@pytest.mark.integration` |

Módulos: `identity`, `catalog`, `stock`, `orders`, `payments`, `consent`, `audit`.

### 4.3 Regras

- **Transação:** um caso de uso = uma unidade de trabalho; o caso de uso chama `commit()`.
  Repositórios, auditoria e outbox nunca fazem commit. Pedido + reserva + auditoria + outbox numa
  só transação, com `SELECT ... FOR UPDATE` ordenado por `id_produto` (RNF-11). O pagamento usa
  duas transações curtas, com a chamada ao gateway fora delas (D-054).
- **Erros:** o domínio levanta `NotFoundError` (404), `BusinessRuleViolationError` (409) ou
  `DomainError` (422), com `codigo` em MAIÚSCULAS e `detalhes` `{field, issue}` quando houver
  campo. A aplicação usa `AuthenticationError` (401), `PermissionDeniedError` (403),
  `ConflictError` (409), `ApplicationValidationError` (422) e `DependencyTimeoutError` (504),
  criados pelo pedaço B. Nunca `HTTPException` nos casos de uso.
- **JSON:** schemas Pydantic com `alias_generator=to_camel` e `populate_by_name=True`; respostas
  nunca trazem `senha_hash` nem dados de outro cliente (RNF-05).
- **Paginação:** `?page=1&limit=10` (máximo 100); resposta `{items, page, limit, total}`.
- **Auditoria:** `PEDIDO_CRIADO`, `STATUS_ALTERADO`, `PAGAMENTO_APROVADO`, `PAGAMENTO_RECUSADO`,
  `CONSENTIMENTO_REGISTRADO`, na mesma transação; `detalhes` sem PII.
- **Eventos:** subclasses de `DomainEvent` com `event_type` explícito e payload sem PII.
- **Logs:** nunca e-mail, nome, senha, token ou corpo de requisição.
- **Dependências:** já adicionadas no `main` (`argon2-cffi`, `PyJWT`, `httpx`). Ninguém mexe em
  `pyproject.toml` nem nos `.lock`. Configuração nova (ex.: `JWT_SECRET`, `PAYMENT_GATEWAY_URL`)
  entra em `config.py`, `.env.example` (valor fictício) e `scripts/setup_env.py` (segredo
  aleatório), e só o pedaço B mexe nesses arquivos; C informa no relatório a variável de que
  precisa.
- **Senhas de demonstração:** a carga inicial usa senhas fictícias documentadas no README só para
  uso local (ex.: `Demo@2026`); nunca senhas reais.

### 4.4 Ambiente de cada agente (worktree)

- Rode `make setup` na raiz da worktree e, **sem exibir o `.env`**, troque as portas:
  `sed -i 's/^API_PORT=.*/API_PORT=<api>/; s/^DB_HOST_PORT=.*/DB_HOST_PORT=<db>/' .env`.
  Portas: A 8141/55441, B 8142/55442, C 8143/55443, E 8145/55445, F 8146/55446.
- **Nunca** exiba, copie ou leia `.env`, `.registro-ia.local` ou credenciais.
- Antes de concluir: `make lint`, `make typecheck`, `make test` e, se usa banco,
  `make migrate && make test-integration`, todos verdes. Depois `docker compose down -v`.
- Commits pequenos no seu branch, em português, no estilo `feat: ...`, terminando com a linha
  `Co-Authored-By` indicada na tarefa. Sem push e sem merge.

### 4.5 Relatório final de cada agente

Arquivos criados; decisões tomadas que não estavam especificadas (vão para o registro humano × IA);
dúvidas em aberto; resultado dos comandos de verificação.
