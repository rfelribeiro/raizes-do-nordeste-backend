# Coleção Postman do MVP

Coleção `raizes-mvp.postman_collection.json` (formato v2.1) e ambiente `local.postman_environment.json`.
Cobre o fluxo A: pedido, pagamento mock aprovado ou recusado, status, consentimento e auditoria
(13 cenários positivos e 10 negativos, mais o login dos 7 perfis e o login com senha errada).
Cada requisição tem testes `pm.test`; tokens e ids ficam em variáveis de coleção.

A coleção é repetível: cada execução cria pedidos novos e não depende de contadores fixos.

## Importar no Postman

1. Importe `postman/raizes-mvp.postman_collection.json` e `postman/local.postman_environment.json`.
2. Selecione o ambiente "Raizes local" e ajuste `baseUrl` para a porta da sua API (`API_PORT`).
3. Rode a coleção inteira (Runner) na ordem das pastas: `00 Autenticacao`, `01 Positivos`, `02 Negativos`.

A senha `senhaDemo` do ambiente é **fictícia** (carga inicial de demonstração, uso local). Nunca use
senhas reais aqui.

## Rodar com newman (`make postman`)

Pré-requisitos: `make setup`, `make up`, `make migrate` e `make seed`.

```bash
make postman
```

Roda `postman/newman:6.2.1-alpine` em contêiner (`--network host`) com `baseUrl` apontando para
`http://localhost:<API_PORT do .env>`.

## Cenários

| Cenario | Descricao | Requisito/regra | Status esperado | Tipo |
|---|---|---|---|---|
| 00 | Login dos 7 perfis | RF-02 | 200 | Positivo |
| 00 | Login com senha errada | RF-02, RNF-03 | 401 | Negativo |
| P01 | Cliente cria pedido APP | RF-07, RN-12 | 201 | Positivo |
| P02 | Listar com canalPedido=APP | RF-08 | 200 | Positivo |
| P03 | Cliente obtem o proprio pedido | RF-08 | 200 | Positivo |
| P04 | Pagamento recusado (tok_recusado) | RF-11, RF-12, UC-05 | 201 (RECUSADO) | Positivo (pagamento negado) |
| P05 | Pedido segue AGUARDANDO_PAGAMENTO | UC-05 | 200 | Positivo |
| P06 | Pagamento aprovado (tok_aprovado) | RF-11, UC-05 | 201 (PAGO) | Positivo |
| P07 | Cozinha: EM_PREPARO | RF-09, RN-03, RN-04 | 200 | Positivo |
| P08 | Cozinha: PRONTO | RF-09, RN-03, RN-04 | 200 | Positivo |
| P09 | Atendente: ENTREGUE | RF-09, RN-04 | 200 | Positivo |
| P10 | Atendente cria pedido BALCAO | RF-07, RN-14 | 201 | Positivo |
| P11 | Registrar consentimento MARKETING | RF-14 | 201 | Positivo |
| P12 | Listar consentimentos | RF-14 | 200 | Positivo |
| P13 | Auditoria PEDIDO_CRIADO (admin) | RF-13, UC-11 | 200 | Positivo (auditoria) |
| N01 | Criar pedido sem token | RNF-03 | 401 | Negativo |
| N02 | Cozinha cria pedido | RN-14, RNF-03 | 403 | Negativo |
| N03 | Cliente muda status | RN-04, RNF-03 | 403 | Negativo |
| N04 | canalPedido ausente | RF-07, RN-12 | 422 | Negativo |
| N05 | Canal incompativel com o perfil | RN-14 | 422 | Negativo |
| N06 | Pedido inexistente | RNF-03 | 404 | Negativo |
| N07 | Cliente2 le pedido de outro cliente | RNF-05 | 404 | Negativo |
| N08 | Quantidade acima do estoque | RF-07, RNF-11 | 409 ESTOQUE_INSUFICIENTE | Negativo |
| N09 | Transicao ENTREGUE para PRONTO | RN-03 | 409 TRANSICAO_INVALIDA | Negativo |
| N10 | Pagar pedido ja pago | UC-05 | 409 | Negativo |

Todos os negativos validam o erro padrão (`error`, `message`, `details`, `timestamp`, `path`,
`requestId`; ver [docs/api](../docs/api/README.md)). Pagamento negado: P04. Auditoria: P13.
