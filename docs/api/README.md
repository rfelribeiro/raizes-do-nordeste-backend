# API

Descrição do contrato HTTP. A especificação OpenAPI é gerada automaticamente pela aplicação em
execução e reflete os mesmos contratos descritos aqui:

- Swagger UI: `http://localhost:${API_PORT}/docs`
- OpenAPI JSON: `http://localhost:${API_PORT}/openapi.json`

O contrato segue o roteiro oficial da trilha (Roteiro de Atividade Prática da Trilha Back-end, 2026) e está todo em
português ([ADR 0010](../arquitetura/adr/0010-idioma-portugues.md)). As convenções de campos e
enums estão na seção "Contrato da API" do
[dicionário de dados](../dados/dicionario-de-dados.md#contrato-da-api).

## Convenções de rota

| Item | Convenção |
|---|---|
| Rotas | plural, em português: `/auth`, `/usuarios`, `/unidades`, `/produtos`, `/estoques`, `/pedidos` (pagamento como subrecurso: `/pedidos/{id}/pagamentos`), `/fidelidade`, `/consentimentos`, `/auditoria`. Implementados: `/auth`, `/pedidos`, `/consentimentos` e `/auditoria`; os demais estão modelados, sem código |
| Prefixo | os endpoints de negócio ficam sob `/api/v1` (ex.: `POST /api/v1/pedidos`); os health checks ficam na raiz (`/health/live`, `/health/ready`) |
| Autenticação | header `Authorization: Bearer <accessToken>`, obtido em `POST /api/v1/auth/login` (validade de 3600 s) |
| Campos JSON | `camelCase` em português: `canalPedido`, `clienteId`, `unidadeId`, `itens`, `produtoId`, `quantidade`, `formaPagamento`, `precoUnitario`, `criadoEm` |
| Enums | MAIÚSCULAS, sem acento: `AGUARDANDO_PAGAMENTO`; `canalPedido`: `APP`, `TOTEM`, `BALCAO`, `PICKUP`, `WEB` |
| Valores monetários | string decimal com 2 casas (`"12.00"`) |
| Datas | ISO-8601 em UTC (`2026-11-22T18:38:46.145495Z`) |
| Identificadores | UUID |
| Paginação | `?page=1&limit=10` (nomes do roteiro; `limit` máximo 100); resposta `{items, page, limit, total}` |
| Rastreio | header `X-Request-ID` (gerado se ausente e devolvido na resposta) |

## Endpoints implementados

Os exemplos desta página são **respostas reais** da API em execução com os dados de `make seed`:
o `accessToken` aparece abreviado (`"eyJ..."`), os e-mails são do domínio reservado `@exemplo.com`
e a senha `Demo@2026` é **fictícia**, só para demonstração local. Todo erro (4xx e 5xx) segue o
[formato de erro](#formato-de-erro).

| Recurso | Endpoint | Perfis | Sucesso |
|---|---|---|---|
| Autenticação | [`POST /api/v1/auth/login`](#autenticação--login) | público | 200 |
| Pedidos | [`POST /api/v1/pedidos`](#pedidos--criar-pedido) | CLIENTE, ATENDENTE, GERENTE | 201 |
| Pedidos | [`GET /api/v1/pedidos`](#pedidos--listar-pedidos) | qualquer perfil autenticado (escopo por perfil) | 200 |
| Pedidos | [`GET /api/v1/pedidos/{id}`](#pedidos--obter-pedido) | qualquer perfil autenticado (escopo por perfil) | 200 |
| Pedidos | [`PATCH /api/v1/pedidos/{id}/status`](#pedidos--atualizar-status) | COZINHA, ATENDENTE, GERENTE | 200 |
| Pagamentos | [`POST /api/v1/pedidos/{id}/pagamentos`](#pagamentos--solicitar-pagamento) | CLIENTE (dono do pedido) | 201 |
| Consentimentos | [`POST /api/v1/consentimentos`](#consentimentos--registrar-consentimento) | CLIENTE | 201 |
| Consentimentos | [`GET /api/v1/consentimentos`](#consentimentos--listar-consentimentos) | CLIENTE | 200 |
| Auditoria | [`GET /api/v1/auditoria`](#auditoria--consultar-trilha) | ADMIN, GERENTE | 200 |
| Saúde | [`GET /health/live` e `GET /health/ready`](#saúde--health-checks) | público | 200 |

### Autenticação — Login

- **Finalidade:** autentica o usuário e emite o JWT usado nas demais chamadas.
- **Método/Rota:** `POST /api/v1/auth/login`
- **Auth/Permissão:** (X) público | Perfis: todos
- **Parâmetros:** Path: nenhum | Query: nenhum

Request (JSON):

```jsonc
{
  "email": "cliente@exemplo.com",
  "senha": "Demo@2026"  // senha fictícia de demonstração; segredos:permitir
}
```

Response 200 (JSON):

```json
{
  "accessToken": "eyJ...",
  "tokenType": "bearer",
  "expiresIn": 3600
}
```

- **Status codes:** 200 sucesso; 401 credenciais inválidas (mensagem única, sem revelar se o e-mail existe); 422 corpo inválido.
- **Erros (padrão):** 401:

```json
{
  "error": "NAO_AUTENTICADO",
  "message": "E-mail ou senha inválidos.",
  "details": [],
  "timestamp": "2026-11-22T18:38:46Z",
  "path": "/api/v1/auth/login",
  "requestId": "181f603eef934624b5edffd18916fad3"
}
```

422 (campo ausente):

```json
{
  "error": "VALIDACAO_FALHOU",
  "message": "Um ou mais campos da requisição são inválidos.",
  "details": [{"field": "senha", "issue": "Field required"}],
  "timestamp": "2026-11-22T18:38:46Z",
  "path": "/api/v1/auth/login",
  "requestId": "a389e48451ea46908da8bbd243e2d05b"
}
```

### Pedidos — Criar pedido

- **Finalidade:** cria um pedido em `AGUARDANDO_PAGAMENTO` e reserva o estoque, de forma atômica (o pedido expira em 15 minutos).
- **Método/Rota:** `POST /api/v1/pedidos`
- **Auth/Permissão:** (X) JWT | Perfis: CLIENTE (canais `APP`, `WEB`, `PICKUP`); ATENDENTE e GERENTE da unidade (canais `BALCAO`, `TOTEM`, com `clienteId` opcional)
- **Parâmetros:** Path: nenhum | Query: nenhum

Request (JSON):

```json
{
  "unidadeId": "00000000-0000-4000-8000-000000000101",
  "canalPedido": "APP",
  "itens": [
    {"produtoId": "00000000-0000-4000-8000-000000000301", "quantidade": 2}
  ]
}
```

Response 201 (JSON; o header `Location` aponta para o novo pedido):

```json
{
  "id": "cd7d06be-f5d9-4213-829a-be1184d5c4a7",
  "numeroPedido": 1,
  "unidadeId": "00000000-0000-4000-8000-000000000101",
  "clienteId": "00000000-0000-4000-8000-000000000401",
  "canalPedido": "APP",
  "status": "AGUARDANDO_PAGAMENTO",
  "itens": [
    {
      "produtoId": "00000000-0000-4000-8000-000000000301",
      "quantidade": 2,
      "precoUnitario": "12.00",
      "valorTotalItem": "24.00"
    }
  ],
  "valorItens": "24.00",
  "valorDesconto": "0.00",
  "valorTotal": "24.00",
  "expiraEm": "2026-11-22T18:53:46.145495Z",
  "criadoEm": "2026-11-22T18:38:46.145495Z"
}
```

- **Status codes:** 201 criado; 401 sem token ou token inválido; 403 perfil sem permissão (ex.: COZINHA); 404 unidade ou produto inexistente; 409 `ESTOQUE_INSUFICIENTE`; 422 validação (`canalPedido` ausente, inválido ou incompatível com o perfil; `quantidade` fora de 1 a 999; corpo JSON malformado).
- **Erros (padrão):** 409 estoque insuficiente (carne de sol: 5 unidades pedidas, 2 disponíveis):

```json
{
  "error": "ESTOQUE_INSUFICIENTE",
  "message": "Não há quantidade suficiente para um ou mais itens.",
  "details": [
    {"field": "produtoId", "issue": "produto 00000000-0000-4000-8000-000000000304: disponível 2"}
  ],
  "timestamp": "2026-11-22T18:38:46Z",
  "path": "/api/v1/pedidos",
  "requestId": "6ac2d4444ea34045b978278160272f79"
}
```

422 com `canalPedido` inválido:

```json
{
  "error": "VALIDACAO_FALHOU",
  "message": "Um ou mais campos da requisição são inválidos.",
  "details": [
    {"field": "canalPedido", "issue": "Input should be 'APP', 'TOTEM', 'BALCAO', 'PICKUP' or 'WEB'"}
  ],
  "timestamp": "2026-11-22T18:38:46Z",
  "path": "/api/v1/pedidos",
  "requestId": "572c8553bc3f4c17960615a819945cb6"
}
```

422 com `canalPedido` ausente e quantidade inválida (vários campos na mesma resposta):

```json
{
  "error": "VALIDACAO_FALHOU",
  "message": "Um ou mais campos da requisição são inválidos.",
  "details": [
    {"field": "canalPedido", "issue": "Field required"},
    {"field": "itens[0].quantidade", "issue": "Input should be greater than or equal to 1"}
  ],
  "timestamp": "2026-11-22T18:38:46Z",
  "path": "/api/v1/pedidos",
  "requestId": "e78258c05c744d8fb89fe74ab488c314"
}
```

422 com canal incompatível com o perfil (CLIENTE usando `BALCAO`):

```json
{
  "error": "VALIDACAO_FALHOU",
  "message": "Canal incompatível com o perfil.",
  "details": [
    {"field": "canalPedido", "issue": "o perfil CLIENTE não pode criar pedido no canal BALCAO"}
  ],
  "timestamp": "2026-11-22T18:38:46Z",
  "path": "/api/v1/pedidos",
  "requestId": "4e2787f6f7e14923b3733f793abf9887"
}
```

401 (sem token) e 403 (COZINHA criando pedido), respectivamente:

```json
{"error": "NAO_AUTENTICADO", "message": "Autenticação necessária.", "details": [], "timestamp": "2026-11-22T18:38:46Z", "path": "/api/v1/pedidos", "requestId": "a1d37ac949af4f52a73e421ba60f54b7"}
{"error": "SEM_PERMISSAO", "message": "Você não tem permissão para esta operação.", "details": [], "timestamp": "2026-11-22T18:38:46Z", "path": "/api/v1/pedidos", "requestId": "9ddf14a88852437fb7883bee71255490"}
```

### Pedidos — Listar pedidos

- **Finalidade:** lista pedidos paginados, filtráveis por canal, status e unidade, no escopo do perfil.
- **Método/Rota:** `GET /api/v1/pedidos`
- **Auth/Permissão:** (X) JWT | Perfis: CLIENTE (só os seus); COZINHA, ATENDENTE e GERENTE (só a sua unidade); ADMIN (todos)
- **Parâmetros:** Path: nenhum | Query: `canalPedido` (`APP`, `TOTEM`, `BALCAO`, `PICKUP`, `WEB`), `status`, `unidadeId` (UUID), `page` (padrão 1), `limit` (padrão 10, máximo 100)

Request: sem corpo. Exemplo: `GET /api/v1/pedidos?canalPedido=PICKUP&page=1&limit=10`

Response 200 (JSON):

```json
{
  "items": [
    {
      "id": "48f477a4-e873-49ed-a96d-a0cdb7ed9dea",
      "numeroPedido": 2,
      "unidadeId": "00000000-0000-4000-8000-000000000101",
      "clienteId": "00000000-0000-4000-8000-000000000401",
      "canalPedido": "PICKUP",
      "status": "PAGO",
      "itens": [
        {
          "produtoId": "00000000-0000-4000-8000-000000000301",
          "quantidade": 1,
          "precoUnitario": "12.00",
          "valorTotalItem": "12.00"
        }
      ],
      "valorItens": "12.00",
      "valorDesconto": "0.00",
      "valorTotal": "12.00",
      "expiraEm": "2026-11-22T18:54:01.941951Z",
      "criadoEm": "2026-11-22T18:39:01.941951Z"
    }
  ],
  "page": 1,
  "limit": 10,
  "total": 1
}
```

- **Status codes:** 200 sucesso; 401 sem token ou token inválido; 422 filtro ou paginação inválidos.
- **Erros (padrão):** 422 com `canalPedido=XYZ` (o `field` de erros de query leva o prefixo `query.`):

```json
{
  "error": "VALIDACAO_FALHOU",
  "message": "Um ou mais campos da requisição são inválidos.",
  "details": [
    {"field": "query.canalPedido", "issue": "Input should be 'APP', 'TOTEM', 'BALCAO', 'PICKUP' or 'WEB'"}
  ],
  "timestamp": "2026-11-22T18:39:11Z",
  "path": "/api/v1/pedidos",
  "requestId": "82ae4cbebf6d40e98dc9059aa6496d2b"
}
```

### Pedidos — Obter pedido

- **Finalidade:** consulta um pedido com seus itens.
- **Método/Rota:** `GET /api/v1/pedidos/{id}`
- **Auth/Permissão:** (X) JWT | Perfis: CLIENTE (só os seus), colaboradores (só a sua unidade), ADMIN
- **Parâmetros:** Path: `id` (UUID do pedido) | Query: nenhum

Request: sem corpo.

Response 200 (JSON): o mesmo objeto de pedido devolvido na criação (ver [Criar pedido](#pedidos--criar-pedido)), com o `status` atual.

- **Status codes:** 200; 401; 403 colaborador de outra unidade; 404 pedido inexistente ou de outro cliente (a existência não é revelada); 422 `id` que não é UUID.
- **Erros (padrão):** 404:

```json
{
  "error": "NAO_ENCONTRADO",
  "message": "Pedido não encontrado.",
  "details": [],
  "timestamp": "2026-11-22T18:39:11Z",
  "path": "/api/v1/pedidos/48f477a4-e873-49ed-a96d-a0cdb7ed9dea",
  "requestId": "abe4338fe6574011bffb994a10ed63ed"
}
```

403 (gerente de outra unidade):

```json
{
  "error": "SEM_PERMISSAO",
  "message": "Este pedido pertence a outra unidade.",
  "details": [],
  "timestamp": "2026-11-22T18:39:11Z",
  "path": "/api/v1/pedidos/48f477a4-e873-49ed-a96d-a0cdb7ed9dea",
  "requestId": "665016db2fe3417ea61d8efab674160b"
}
```

### Pedidos — Atualizar status

- **Finalidade:** avança o status do pedido pela máquina de estados (RN-03), conforme o perfil (RN-04).
- **Método/Rota:** `PATCH /api/v1/pedidos/{id}/status`
- **Auth/Permissão:** (X) JWT | Perfis: COZINHA (`PAGO` para `EM_PREPARO` e `PRONTO`); ATENDENTE e GERENTE (`PRONTO` para `ENTREGUE`; GERENTE só na própria unidade). O perfil é verificado antes da máquina de estados (403 antes de 409).
- **Parâmetros:** Path: `id` (UUID do pedido) | Query: nenhum

Request (JSON; `motivo` é opcional, até 255 caracteres):

```json
{
  "status": "EM_PREPARO"
}
```

Response 200 (JSON): o pedido com o novo `status` (mesmo objeto da criação):

```json
{
  "id": "48f477a4-e873-49ed-a96d-a0cdb7ed9dea",
  "numeroPedido": 2,
  "unidadeId": "00000000-0000-4000-8000-000000000101",
  "clienteId": "00000000-0000-4000-8000-000000000401",
  "canalPedido": "PICKUP",
  "status": "EM_PREPARO",
  "itens": [
    {
      "produtoId": "00000000-0000-4000-8000-000000000301",
      "quantidade": 1,
      "precoUnitario": "12.00",
      "valorTotalItem": "12.00"
    }
  ],
  "valorItens": "12.00",
  "valorDesconto": "0.00",
  "valorTotal": "12.00",
  "expiraEm": "2026-11-22T18:54:01.941951Z",
  "criadoEm": "2026-11-22T18:39:01.941951Z"
}
```

- **Status codes:** 200; 401; 403 perfil sem permissão ou transição que o perfil não pode solicitar; 404; 409 `TRANSICAO_INVALIDA`; 422 `status` fora do enum.
- **Erros (padrão):** 409 (pedido já em `EM_PREPARO`; o gerente pede `EM_PREPARO` de novo):

```json
{
  "error": "TRANSICAO_INVALIDA",
  "message": "Transição de EM_PREPARO para EM_PREPARO não é permitida.",
  "details": [{"field": "status", "issue": "EM_PREPARO -> EM_PREPARO"}],
  "timestamp": "2026-11-22T18:39:19Z",
  "path": "/api/v1/pedidos/48f477a4-e873-49ed-a96d-a0cdb7ed9dea/status",
  "requestId": "7ded723d0d61461dbfa871cbc0b860a8"
}
```

403 (COZINHA tentando `ENTREGUE`):

```json
{
  "error": "SEM_PERMISSAO",
  "message": "Você não pode solicitar esta mudança de status.",
  "details": [{"field": "status", "issue": "perfil não pode solicitar esta transição"}],
  "timestamp": "2026-11-22T18:39:11Z",
  "path": "/api/v1/pedidos/48f477a4-e873-49ed-a96d-a0cdb7ed9dea/status",
  "requestId": "10901e13efa549789857243ce709f4c9"
}
```

### Pagamentos — Solicitar pagamento

- **Finalidade:** solicita o pagamento do pedido ao gateway mock; aprovado, o pedido vira `PAGO` e o estoque reservado é baixado.
- **Método/Rota:** `POST /api/v1/pedidos/{id}/pagamentos`
- **Auth/Permissão:** (X) JWT | Perfis: CLIENTE dono do pedido
- **Parâmetros:** Path: `id` (UUID do pedido) | Query: nenhum

Request (JSON; `formaPagamento`: `PIX`, `CREDITO` ou `DEBITO`; `tokenPagamento` de teste: `tok_aprovado`, `tok_recusado` ou `tok_timeout`):

```json
{
  "formaPagamento": "PIX",
  "tokenPagamento": "tok_aprovado"
}
```

Response 201 (JSON), pagamento aprovado:

```json
{
  "tentativa": {
    "id": "60df392b-7b2d-4b3f-9462-7c374afeac66",
    "numeroTentativa": 1,
    "formaPagamento": "PIX",
    "status": "APROVADO",
    "valor": "12.00",
    "motivoRecusa": null,
    "qtdChamadasGateway": 1,
    "idTransacaoGateway": "txn_39ac1ce23aed4d60",
    "solicitadoEm": "2026-11-22T18:39:02.039468Z",
    "respondidoEm": "2026-11-22T18:39:02.057284Z"
  },
  "statusPedido": "PAGO"
}
```

Response 201 (JSON), pagamento recusado (`tok_recusado`): a resposta continua 201; o pedido permanece em `AGUARDANDO_PAGAMENTO`, com a reserva mantida, e o cliente pode tentar de novo:

```json
{
  "tentativa": {
    "id": "507651ae-2313-4fdc-9f6e-d128d6dccc5d",
    "numeroTentativa": 1,
    "formaPagamento": "CREDITO",
    "status": "RECUSADO",
    "valor": "12.00",
    "motivoRecusa": "Pagamento recusado pelo emissor (simulação)",
    "qtdChamadasGateway": 1,
    "idTransacaoGateway": null,
    "solicitadoEm": "2026-11-22T18:39:02.096218Z",
    "respondidoEm": "2026-11-22T18:39:02.108160Z"
  },
  "statusPedido": "AGUARDANDO_PAGAMENTO"
}
```

- **Status codes:** 201 tentativa registrada (aprovada ou recusada); 401; 403 perfil diferente de CLIENTE; 404 pedido inexistente ou de outro cliente; 409 `PEDIDO_FORA_DE_AGUARDANDO_PAGAMENTO`; 422 forma ou token inválidos; 504 `TEMPO_ESGOTADO` (gateway sem resposta em 3 s, após 2 novas chamadas; a resposta leva cerca de 9 s e o pedido permanece aguardando pagamento).
- **Erros (padrão):** 409 (pedido já pago):

```json
{
  "error": "PEDIDO_FORA_DE_AGUARDANDO_PAGAMENTO",
  "message": "O pedido não está aguardando pagamento.",
  "details": [{"field": "status", "issue": "PAGO"}],
  "timestamp": "2026-11-22T18:39:02Z",
  "path": "/api/v1/pedidos/48f477a4-e873-49ed-a96d-a0cdb7ed9dea/pagamentos",
  "requestId": "6626700f3cf644728848cb24660efc65"
}
```

504 (`tok_timeout`):

```json
{
  "error": "TEMPO_ESGOTADO",
  "message": "O gateway de pagamento não respondeu a tempo.",
  "details": [],
  "timestamp": "2026-11-22T18:39:11Z",
  "path": "/api/v1/pedidos/a9d1a04f-33d2-4051-824f-54df8784d69b/pagamentos",
  "requestId": "adf508807a1348fca0cd8debd9dc5e1a"
}
```

### Consentimentos — Registrar consentimento

- **Finalidade:** registra a concessão ou a revogação de um consentimento (LGPD); o registro é append-only e o vigente é o último de cada finalidade.
- **Método/Rota:** `POST /api/v1/consentimentos`
- **Auth/Permissão:** (X) JWT | Perfis: CLIENTE
- **Parâmetros:** Path: nenhum | Query: nenhum

Request (JSON; `finalidade`: `FIDELIDADE`, `MARKETING` ou `DATA_NASCIMENTO`; `acao`: `CONCEDIDO` ou `REVOGADO`):

```json
{
  "finalidade": "MARKETING",
  "acao": "CONCEDIDO",
  "versaoTermo": "v1"
}
```

Response 201 (JSON):

```json
{
  "id": "5d8cf352-1bdc-4a4d-a1fa-62faf6042294",
  "finalidade": "MARKETING",
  "acao": "CONCEDIDO",
  "baseLegal": "Consentimento (LGPD art. 7º, I)",
  "versaoTermo": "v1",
  "registradoEm": "2026-11-22T18:39:11.432380Z"
}
```

- **Status codes:** 201; 401; 403 perfil diferente de CLIENTE; 409 `CONSENTIMENTO_JA_CONCEDIDO` (concessão repetida ou revogação sem consentimento vigente); 422.
- **Erros (padrão):** 409:

```json
{
  "error": "CONSENTIMENTO_JA_CONCEDIDO",
  "message": "A finalidade já está concedida.",
  "details": [],
  "timestamp": "2026-11-22T18:39:11Z",
  "path": "/api/v1/consentimentos",
  "requestId": "3c70f002d7394cf083b048154e179d7e"
}
```

### Consentimentos — Listar consentimentos

- **Finalidade:** lista o histórico dos próprios consentimentos e o vigente por finalidade.
- **Método/Rota:** `GET /api/v1/consentimentos`
- **Auth/Permissão:** (X) JWT | Perfis: CLIENTE
- **Parâmetros:** Path: nenhum | Query: nenhum

Request: sem corpo.

Response 200 (JSON):

```json
{
  "historico": [
    {
      "id": "5d8cf352-1bdc-4a4d-a1fa-62faf6042294",
      "finalidade": "MARKETING",
      "acao": "CONCEDIDO",
      "baseLegal": "Consentimento (LGPD art. 7º, I)",
      "versaoTermo": "v1",
      "registradoEm": "2026-11-22T18:39:11.432380Z"
    }
  ],
  "vigentes": [
    {
      "id": "5d8cf352-1bdc-4a4d-a1fa-62faf6042294",
      "finalidade": "MARKETING",
      "acao": "CONCEDIDO",
      "baseLegal": "Consentimento (LGPD art. 7º, I)",
      "versaoTermo": "v1",
      "registradoEm": "2026-11-22T18:39:11.432380Z"
    }
  ]
}
```

- **Status codes:** 200; 401; 403 perfil diferente de CLIENTE.
- **Erros (padrão):** o formato padrão (ex.: 403 `SEM_PERMISSAO`, "Você não tem permissão para esta operação.").

### Auditoria — Consultar trilha

- **Finalidade:** consulta a trilha de auditoria, do registro mais recente ao mais antigo; os `detalhes` nunca trazem dados pessoais.
- **Método/Rota:** `GET /api/v1/auditoria`
- **Auth/Permissão:** (X) JWT | Perfis: ADMIN (toda a rede), GERENTE (só a sua unidade)
- **Parâmetros:** Path: nenhum | Query: `acao` (ex.: `PEDIDO_CRIADO`, `STATUS_ALTERADO`, `PAGAMENTO_APROVADO`, `PAGAMENTO_RECUSADO`, `CONSENTIMENTO_REGISTRADO`), `tipoRecurso` (ex.: `PEDIDO`), `page`, `limit`

Request: sem corpo. Exemplo: `GET /api/v1/auditoria?acao=PEDIDO_CRIADO&limit=1`

Response 200 (JSON):

```json
{
  "items": [
    {
      "id": "e89514cf-6098-4888-8a73-21b1d9e4ed14",
      "ocorridoEm": "2026-11-22T18:39:01.966094Z",
      "usuarioId": "00000000-0000-4000-8000-000000000401",
      "perfil": "CLIENTE",
      "acao": "PEDIDO_CRIADO",
      "tipoRecurso": "PEDIDO",
      "idRecurso": "a9d1a04f-33d2-4051-824f-54df8784d69b",
      "unidadeId": "00000000-0000-4000-8000-000000000101",
      "canalPedido": "WEB",
      "idRequisicao": "19fa3e4733cd413e9bebf1336f853ae3",
      "detalhes": {"qtdItens": 1, "valorTotal": "12.00", "numeroPedido": 3}
    }
  ],
  "page": 1,
  "limit": 1,
  "total": 3
}
```

- **Status codes:** 200; 401; 403 perfil sem permissão (CLIENTE, COZINHA, ATENDENTE); 422.
- **Erros (padrão):** 403:

```json
{
  "error": "SEM_PERMISSAO",
  "message": "Você não tem permissão para esta operação.",
  "details": [],
  "timestamp": "2026-11-22T18:39:11Z",
  "path": "/api/v1/auditoria",
  "requestId": "1a59f58eea0b491e8fd1bdedb65284f2"
}
```

### Saúde — Health checks

- **Finalidade:** informar se o processo está vivo (`live`) e se está pronto para receber tráfego, com o banco respondendo (`ready`).
- **Método/Rota:** `GET /health/live` e `GET /health/ready` (sem o prefixo `/api/v1`)
- **Auth/Permissão:** (X) público
- **Parâmetros:** Path: nenhum | Query: nenhum

Response 200 (JSON): `{"status": "live"}` e `{"status": "ready"}`.

- **Status codes:** 200; 503 `SERVICO_INDISPONIVEL` em `/health/ready` quando o banco não responde.
- **Erros (padrão):** `{"error": "SERVICO_INDISPONIVEL", "message": "O banco de dados não respondeu.", ...}`, no formato padrão.

Rota inexistente e método não permitido também usam o formato padrão: `GET /api/v1/nada`
devolve 404 `NAO_ENCONTRADO` ("Recurso não encontrado.") e `DELETE /api/v1/pedidos` devolve 405
`METODO_NAO_PERMITIDO` ("Método HTTP não permitido para esta rota.", com o header `Allow`).

## Formato de erro

Decisão: [ADR 0011](../arquitetura/adr/0011-formato-de-erro.md). **Toda** resposta de erro (4xx e
5xx, inclusive rota inexistente, método não permitido, validação e falha inesperada) usa
`Content-Type: application/json` e o corpo abaixo, documentado no OpenAPI como `ErroPadrao`
(exemplo real de uma resposta 409):

```json
{
  "error": "ESTOQUE_INSUFICIENTE",
  "message": "Não há quantidade suficiente para um ou mais itens.",
  "details": [
    {"field": "produtoId", "issue": "produto 00000000-0000-4000-8000-000000000304: disponível 2"}
  ],
  "timestamp": "2026-11-22T18:38:46Z",
  "path": "/api/v1/pedidos",
  "requestId": "6ac2d4444ea34045b978278160272f79"
}
```

| Campo | Descrição |
|---|---|
| `error` | Código estável em MAIÚSCULAS, para o cliente tratar por programa |
| `message` | Mensagem legível em português |
| `details` | Lista de `{field, issue}`; `field` usa a notação `campo.sub[0].x` (sem o prefixo `body`; erros de query e de path levam `query.` e `path.`); vazia quando não há detalhe por campo. Nas falhas de validação do Pydantic, `issue` permanece em inglês (ex.: `Field required`) |
| `timestamp` | Instante do erro em UTC (ISO-8601) |
| `path` | Rota requisitada (inclui o prefixo `/api/v1`) |
| `requestId` | Valor de `X-Request-ID`, para correlacionar com os logs |

| Status | `error` |
|---|---|
| 400 | `REQUISICAO_INVALIDA` (reservado; hoje o corpo JSON malformado devolve 422) |
| 401 | `NAO_AUTENTICADO` |
| 403 | `SEM_PERMISSAO` |
| 404 | `NAO_ENCONTRADO` |
| 405 | `METODO_NAO_PERMITIDO` |
| 409 | `CONFLITO` ou o código da regra de negócio (`ESTOQUE_INSUFICIENTE`, `TRANSICAO_INVALIDA`, `PEDIDO_FORA_DE_AGUARDANDO_PAGAMENTO`, `CONSENTIMENTO_JA_CONCEDIDO`) |
| 422 | `VALIDACAO_FALHOU` (com `details` por campo) |
| 500 | `ERRO_INTERNO` (nunca expõe stack nem mensagem interna) |
| 503 | `SERVICO_INDISPONIVEL` (ex.: banco fora do ar em `/health/ready`) |
| 504 | `TEMPO_ESGOTADO` (dependência, como o gateway de pagamento, sem resposta após as novas tentativas) |

Exceções de domínio carregam o próprio `codigo` (e, opcionalmente, `detalhes`), que a camada API
traduz para este formato.
