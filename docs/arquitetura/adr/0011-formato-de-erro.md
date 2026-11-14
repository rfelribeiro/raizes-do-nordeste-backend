# ADR 0011 - Formato de erro do roteiro em todas as respostas

- **Status:** aceita (substitui o uso de RFC 9457 adotado na fundação)
- **Data:** 2026-11-14

## Contexto

A fundação da API devolvia erros no formato **RFC 9457** (`application/problem+json`). O roteiro
oficial da trilha exige "um JSON padrão para todas as falhas", com campos definidos:

```json
{
  "error": "ESTOQUE_INSUFICIENTE",
  "message": "Não há quantidade suficiente para um ou mais itens.",
  "details": [{"field": "itens[0].quantidade", "issue": "Disponível: 1"}],
  "timestamp": "2026-02-05T12:00:00Z",
  "path": "/pedidos",
  "requestId": "uuid-opcional"
}
```

## Decisão

Adotar o formato do roteiro em **toda** resposta de erro, com `Content-Type: application/json`:
erros de domínio e de aplicação, `HTTPException` (inclui 404 de rota inexistente e 405), erros de
validação e falhas inesperadas.

- `error`: código em MAIÚSCULAS; exceções de domínio carregam o próprio `codigo` (ex.:
  `ESTOQUE_INSUFICIENTE`). Códigos genéricos: `REQUISICAO_INVALIDA` (400), `NAO_AUTENTICADO` (401),
  `SEM_PERMISSAO` (403), `NAO_ENCONTRADO` (404), `METODO_NAO_PERMITIDO` (405), `CONFLITO` e códigos
  de regra de negócio (409), `VALIDACAO_FALHOU` (422), `ERRO_INTERNO` (500).
- Validação: 422 com `details` por campo; o `loc` do Pydantic vira `itens[0].quantidade`, sem o
  prefixo `body`.
- `requestId` é o `X-Request-ID` da requisição (também no 500).
- 500 nunca vaza stack nem mensagem interna; o detalhe vai só para o log.
- O schema `ErroPadrao` (com `DetalheErro`) é registrado no OpenAPI como resposta de erro comum
  (400, 401, 403, 404, 409, 422, 500), para o Swagger documentar o padrão.
- Regras de negócio violadas respondem **409** (o roteiro agrupa "conflito/regra de negócio").

## Alternativas consideradas

- **Manter RFC 9457:** é padrão da IETF, mas diverge do formato exigido pelo roteiro.
- **Híbrido** (RFC 9457 e campos do roteiro no mesmo corpo): atende às duas leituras, mas mistura
  `type`/`title`/`status`/`instance` com `error`/`message`/`path`, duplica informação e confunde o
  cliente. Descartado.

## Consequências

- (+) Aderência direta ao roteiro; um único formato para o cliente tratar.
- (+) `requestId` correlaciona a resposta com os logs.
- (-) Abre mão de um padrão aberto (RFC 9457) e do `application/problem+json`.
- (-) As mensagens de validação do Pydantic permanecem no idioma da biblioteca (inglês) no campo
  `issue`.

**Autoria da decisão:** **conjunta.** A IA recomendou adotar o formato do roteiro; o humano aceitou
(D-035). A implementação foi delegada a um agente subordinado, sob especificação.
