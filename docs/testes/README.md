# Plano de testes

Estratégia, como rodar cada nível, cenários T01 a T23 e evidências de execução. O mesmo conteúdo
aparece, resumido, nas seções 6 e 7 do [documento principal](../entrega/documento-principal.md).

## 1. Estratégia

Pirâmide de testes, da base (rápida, muitos) ao topo (lenta, poucos):

| Nível | Onde | O que valida | Banco |
|---|---|---|---|
| Unitários de domínio e aplicação | `tests/unit/` | Máquina de estados, políticas RN-04 e RN-14, reserva de estoque, cliente do gateway, formato do erro padrão, segurança | Nenhum |
| Arquitetura | `tests/architecture/` | Regra de camadas (API, Aplicação, Domínio, Infraestrutura) | Nenhum |
| Integração | `tests/integration/` | Rotas, casos de uso, repositórios, transações, auditoria, outbox e concorrência de estoque, com o gateway de pagamento substituído por um falso | PostgreSQL real, em banco separado `<POSTGRES_DB>_teste` (o de desenvolvimento não é tocado) |
| Ponta a ponta | `postman/raizes-mvp.postman_collection.json` | O fluxo A inteiro via HTTP, contra a API real, o banco real e o **serviço gateway mock real** do Compose | Banco de desenvolvimento, com a carga de `make seed` |

A coleção Postman é a evidência executável exigida pelo roteiro (RT p. 10–12): cada cenário da
seção 3 é uma requisição com testes `pm.test`. Os testes de integração cobrem os mesmos
cenários com mais variações (perfis, unidades, filtros, timeout do gateway, concorrência).

## 2. Como rodar

Pré-requisitos: `make setup` (gera o `.env`), `make up`, `make migrate` e `make seed`.

| Nível | Comando | Observação |
|---|---|---|
| Unitários e arquitetura | `make test` | Sem banco |
| Integração | `make test-integration` | Cria e migra o banco `_teste` sozinho |
| Ponta a ponta | `make postman` | Newman em contêiner; exige `make up` e `make seed` |
| Estilo e tipos | `make lint` e `make typecheck` | |
| Segredos | `make secrets` | |

**Coleção, ordem e token.** Execute as pastas na ordem `00 Autenticacao`, `01 Positivos`,
`02 Negativos`. A pasta `00` faz o login dos sete perfis de demonstração e guarda os tokens em
variáveis de coleção (`tokenCliente`, `tokenAdmin` etc.), então não há token a copiar. O ambiente é
`postman/local.postman_environment.json` (ajuste `baseUrl` para a porta `API_PORT` do seu `.env`);
a senha `senhaDemo` é fictícia. A carga `make seed` define os usuários, as unidades e o estoque
(a carne de sol da unidade 1 tem só 2 unidades, usada no 409). A coleção é repetível: cada
execução cria pedidos novos. Passo a passo da importação manual: [postman/README.md](../../postman/README.md).

Swagger local: `http://localhost:${API_PORT}/docs` (OpenAPI em `/openapi.json`).

## 3. Cenários

IDs T01 a T23: 10 positivos e 13 negativos (mínimo do roteiro: 6 e 4). A coluna Evidência traz o
nome exato da requisição na coleção; a coluna Integração traz o teste automatizado equivalente.

| ID | Cenário | Endpoint | Pré-condição | Entrada | Esperado (status + pontos do response) | Evidência (coleção) | Integração |
|---|---|---|---|---|---|---|---|
| T01 | Login com credenciais válidas | `POST /auth/login` | Carga `make seed` | e-mail e senha de demonstração | 200; `accessToken`, `tokenType` bearer, `expiresIn` 3600 | `Login cliente (200)` (e os outros seis perfis) | n/a (coberto nos fluxos autenticados) |
| T02 | Cliente cria pedido válido | `POST /pedidos` | Token do cliente | `canalPedido` APP, 1 item válido | 201; `status` AGUARDANDO_PAGAMENTO, `valorTotal` calculado, itens | `P01 - Cliente cria pedido APP (201)` | `test_cliente_cria_pedido_e_reserva_estoque` |
| T03 | Listar pedidos filtrando por canal | `GET /pedidos?canalPedido=APP` | Pedido criado em T02 | filtro APP | 200; `items` só com canal APP, `page`, `limit`, `total` | `P02 - Listar pedidos com canalPedido=APP (200)` | `test_filtro_canal_pedido` |
| T04 | Cliente consulta o próprio pedido | `GET /pedidos/{id}` | Pedido de T02 | `id` | 200; pedido com itens | `P03 - Cliente obtem o proprio pedido (200)` | `test_obter_pedido_proprio_com_itens` |
| T05 | Pagamento mock recusado | `POST /pedidos/{id}/pagamentos` | Pedido AGUARDANDO_PAGAMENTO | `tokenPagamento` `tok_recusado` | 201; tentativa RECUSADA com motivo; pedido segue AGUARDANDO_PAGAMENTO e a reserva é mantida | `P04 - Pagamento recusado tok_recusado (201, pedido segue aguardando)` e `P05 - Pedido segue AGUARDANDO_PAGAMENTO apos recusa (200)` | `test_pagamento_recusado_mantem_pedido_e_reserva` |
| T06 | Pagamento mock aprovado | `POST /pedidos/{id}/pagamentos` | Pedido AGUARDANDO_PAGAMENTO | `tokenPagamento` `tok_aprovado` | 201; `statusPedido` PAGO; estoque baixado | `P06 - Pagamento aprovado tok_aprovado (201, pedido PAGO)` | `test_pagamento_aprovado` |
| T07 | Avanço de status pela cozinha e pelo atendente | `PATCH /pedidos/{id}/status` | Pedido PAGO | EM_PREPARO, PRONTO, ENTREGUE | 200 em cada passo; `status` atualizado | `P07 - Cozinha move para EM_PREPARO (200)`, `P08 - Cozinha move para PRONTO (200)`, `P09 - Atendente move para ENTREGUE (200)` | `test_fluxo_completo_de_status` |
| T08 | Atendente cria pedido de balcão | `POST /pedidos` | Token do atendente da unidade 1 | `canalPedido` BALCAO | 201; `canalPedido` BALCAO | `P10 - Atendente cria pedido BALCAO na unidade 1 (201)` | `test_atendente_cria_no_balcao_para_cliente_identificado` |
| T09 | Registrar e listar consentimento | `POST /consentimentos`, `GET /consentimentos` | Token do cliente | finalidade MARKETING, versão do termo | 201 no registro; 200 na lista, com o vigente por finalidade | `P11 - Cliente registra consentimento MARKETING, concedendo ou revogando conforme o vigente (201)` e `P12 - Cliente lista consentimentos (200)` | `test_conceder_revogar_e_vigente` |
| T10 | Ação sensível gera auditoria | `GET /auditoria` | Pedido criado em T02 | `acao=PEDIDO_CRIADO` | 200; registro com o `id` do pedido, sem dados pessoais | `P13 - Auditoria: admin encontra PEDIDO_CRIADO do pedido (200)` | `test_admin_ve_toda_a_rede` |
| T11 | Login com senha errada | `POST /auth/login` | n/a | senha incorreta | 401; erro padrão | `N - Login com senha errada (401)` | n/a |
| T12 | Acesso sem token | `POST /pedidos` | Nenhuma | sem `Authorization` | 401; erro padrão | `N01 - Criar pedido sem token (401)` | `test_sem_token_401` |
| T13 | Perfil sem permissão para criar pedido | `POST /pedidos` | Token da cozinha | pedido válido | 403; erro padrão | `N02 - Cozinha cria pedido (403)` | `test_cozinha_nao_cria_pedido_403` |
| T14 | Cliente tenta mudar status | `PATCH /pedidos/{id}/status` | Token do cliente | EM_PREPARO | 403; erro padrão | `N03 - Cliente tenta mudar status (403)` | `test_perfil_errado_para_o_status_403` |
| T15 | Campo obrigatório ausente | `POST /pedidos` | Token do cliente | corpo sem `canalPedido` | 422 `VALIDACAO_FALHOU`; `details[].field` = `canalPedido` | `N04 - canalPedido ausente (422)` | `test_canal_ausente_retorna_422` |
| T16 | Quantidade negativa (tipo/formato inválido) | `POST /pedidos` | Token do cliente | `quantidade` -1 | 422 `VALIDACAO_FALHOU`; `details[].field` aponta a quantidade do item | `N11 - Quantidade negativa (422)` | `test_quantidade_invalida_422` |
| T17 | Canal incompatível com o perfil | `POST /pedidos` | Token do cliente | `canalPedido` BALCAO | 422; erro padrão | `N05 - Canal incompativel: cliente com BALCAO (422)` | `test_canal_incompativel_com_o_perfil_retorna_422` |
| T18 | Produto inexistente | `POST /pedidos` | Token do cliente | `produtoId` que não existe na carga | 404; erro padrão | `N12 - Produto inexistente (404)` | `test_produto_inexistente_404` |
| T19 | Pedido inexistente | `GET /pedidos/{id}` | Token do cliente | UUID desconhecido | 404; erro padrão | `N06 - Pedido inexistente (404)` | `test_pedido_inexistente_404` (`orders/test_list_get.py`) |
| T20 | Pedido de outro cliente | `GET /pedidos/{id}` | Pedido do cliente 1; token do cliente 2 | `id` do pedido alheio | 404 (não revela a existência); erro padrão | `N07 - Cliente2 obtem pedido do cliente (404)` | `test_pedido_de_outro_cliente_404` (`orders/test_list_get.py`) |
| T21 | Estoque insuficiente | `POST /pedidos` | Carne de sol com 2 unidades na unidade 1 | `quantidade` 3 | 409 `ESTOQUE_INSUFICIENTE`; sem efeito colateral no estoque | `N08 - Quantidade acima do estoque (409 ESTOQUE_INSUFICIENTE)` | `test_estoque_insuficiente_409_sem_efeito_colateral` e `test_varias_criacoes_simultaneas_nao_vendem_mais_que_o_estoque` |
| T22 | Transição de status inválida | `PATCH /pedidos/{id}/status` | Pedido ENTREGUE | PRONTO | 409 `TRANSICAO_INVALIDA` | `N09 - Cozinha pede PRONTO em pedido ENTREGUE: transicao invalida (409)` | `test_transicao_invalida_409` |
| T23 | Pagar pedido já pago | `POST /pedidos/{id}/pagamentos` | Pedido PAGO | `tok_aprovado` | 409; erro padrão | `N10 - Pagar pedido ja pago (409)` | `test_pagar_pedido_ja_pago_409` |

Cobertura além da coleção, só na integração: timeout do gateway com 504 e tentativa registrada
(`test_timeout_retorna_504_e_grava_falha`), escopo por unidade e por cliente, paginação, e a
reserva atômica de estoque sob concorrência.

## 4. Evidências de execução

Resumos em [evidencias/](evidencias/) (sem tokens nem credenciais):

- [newman-resumo.txt](evidencias/newman-resumo.txt): `make postman` duas vezes seguidas, 34
  requisições e 33 asserções, 0 falhas nas duas.
- [pytest-resumo.txt](evidencias/pytest-resumo.txt): `make test` (375 passaram) e
  `make test-integration` (83 passaram).

As capturas de tela do Swagger (`/docs`) são feitas pelo autor e ficam em `docs/testes/evidencias/`.

## 5. Teste de carga

Documentado, **não medido no MVP** (D-057). Meta do RNF-08: p95 abaixo de 300 ms a 50 req/s no
pico. Seria medido com k6, com um cenário de rampa até 50 req/s sobre login, criação e consulta de
pedidos, e o limiar declarado em `thresholds` (`http_req_duration: ['p(95)<300']`). Veja a seção 7.4
do documento principal.
