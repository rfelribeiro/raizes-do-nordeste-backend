# API

Descrição do contrato HTTP. A especificação OpenAPI é gerada automaticamente pela aplicação em
execução:

- Swagger UI: `http://localhost:${API_PORT}/docs`
- OpenAPI JSON: `http://localhost:${API_PORT}/openapi.json`

O contrato segue o roteiro oficial da trilha (Roteiro de Atividade Prática da Trilha Back-end, 2026) e está todo em
português ([ADR 0010](../arquitetura/adr/0010-idioma-portugues.md)). As convenções de campos e
enums estão na seção "Contrato da API" do
[dicionário de dados](../dados/dicionario-de-dados.md#contrato-da-api).

## Convenções de rota

| Item | Convenção |
|---|---|
| Rotas | plural, em português: `/auth`, `/usuarios`, `/unidades`, `/produtos`, `/estoques`, `/pedidos` (pagamento como subrecurso: `/pedidos/{id}/pagamentos`), `/fidelidade`, `/consentimentos`, `/auditoria` |
| Campos JSON | `camelCase` em português: `canalPedido`, `clienteId`, `unidadeId`, `itens`, `produtoId`, `quantidade`, `formaPagamento`, `precoUnitario`, `criadoEm` |
| Enums | MAIÚSCULAS, sem acento: `AGUARDANDO_PAGAMENTO`; `canalPedido`: `APP`, `TOTEM`, `BALCAO`, `PICKUP`, `WEB` |
| Paginação | `?page=1&limit=10` (nomes do roteiro) |
| Rastreio | header `X-Request-ID` (gerado se ausente e devolvido na resposta) |

Hoje existem apenas os health checks (`GET /health/live` e `GET /health/ready`); os módulos de
negócio ainda serão implementados.

## Formato de erro

Decisão: [ADR 0011](../arquitetura/adr/0011-formato-de-erro.md). **Toda** resposta de erro (4xx e
5xx, inclusive rota inexistente, método não permitido, validação e falha inesperada) usa
`Content-Type: application/json` e o corpo abaixo, documentado no OpenAPI como `ErroPadrao`:

```json
{
  "error": "ESTOQUE_INSUFICIENTE",
  "message": "Não há quantidade suficiente para um ou mais itens.",
  "details": [{"field": "itens[0].quantidade", "issue": "Disponível: 1"}],
  "timestamp": "2026-02-05T12:00:00Z",
  "path": "/pedidos",
  "requestId": "9f2c0d6e1b7a4c58"
}
```

| Campo | Descrição |
|---|---|
| `error` | Código estável em MAIÚSCULAS, para o cliente tratar por programa |
| `message` | Mensagem legível em português |
| `details` | Lista de `{field, issue}`; `field` usa a notação `campo.sub[0].x` (sem o prefixo `body`); vazia quando não há detalhe por campo |
| `timestamp` | Instante do erro em UTC (ISO-8601) |
| `path` | Rota requisitada |
| `requestId` | Valor de `X-Request-ID`, para correlacionar com os logs |

| Status | `error` |
|---|---|
| 400 | `REQUISICAO_INVALIDA` |
| 401 | `NAO_AUTENTICADO` |
| 403 | `SEM_PERMISSAO` |
| 404 | `NAO_ENCONTRADO` |
| 405 | `METODO_NAO_PERMITIDO` |
| 409 | `CONFLITO` ou o código da regra de negócio (ex.: `ESTOQUE_INSUFICIENTE`) |
| 422 | `VALIDACAO_FALHOU` (com `details` por campo) |
| 500 | `ERRO_INTERNO` (nunca expõe stack nem mensagem interna) |
| 503 | `SERVICO_INDISPONIVEL` (ex.: banco fora do ar em `/health/ready`) |

Exceções de domínio carregam o próprio `codigo` (e, opcionalmente, `detalhes`), que a camada API
traduz para este formato.
