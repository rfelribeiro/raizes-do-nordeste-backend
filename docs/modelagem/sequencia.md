# Diagramas de sequência

Legenda de origem: 🧑 humana · 🤝 conjunta (a IA propôs, o humano escolheu) · 🤖 IA (pendente de validação). Decisões em [`decisoes.md`](../uso-de-ia/decisoes.md). Requisitos em [`requisitos/README.md`](../requisitos/README.md); casos de uso em [`casos-de-uso.md`](casos-de-uso.md); classes e portas em [`classes.md`](classes.md); tabelas em [`der.md`](der.md). Atende o item 4.4 do roteiro da trilha (sequência do fluxo crítico: pedido, pagamento externo e atualização de status).

## Convenções

Os participantes têm o nome da **camada** e, entre parênteses no texto, a classe. Os diagramas seguem a regra de dependência: a API só fala com o caso de uso (aplicação); o caso de uso orquestra o domínio e as **portas**; a infraestrutura implementa as portas e fala com o PostgreSQL.

| Participante | Camada | Papel |
|---|---|---|
| Cliente / Cozinha | Ator | Origem da requisição HTTP |
| API | `raizes.api` | Router, validação de schema, JWT, tradução de erros para o erro padrão |
| CasoDeUso | `raizes.application` | `CriarPedido`, `SolicitarPagamento`, `AtualizarStatusPedido`; controla a transação |
| Dominio | `raizes.domain` | `Pedido`, `Estoque`, `ContaPontos`, `PoliticaTransicao` |
| Repos | portas da aplicação | `RepositorioPedidos`, `RepositorioEstoques` etc., implementados em `raizes.infrastructure` |
| Auditoria e Outbox | portas da aplicação | `RegistradorAuditoria` e `OutboxWriter`, gravados na transação do caso de uso |
| Gateway | infraestrutura | `GatewayPagamento` (adaptador HTTP do serviço mock, ator externo) |
| BD | infraestrutura | PostgreSQL |

Todo erro sai no formato padrão `{error, message, details[{field, issue}], timestamp, path, requestId}` (RNF-13). Os valores de `error` além de `ESTOQUE_INSUFICIENTE` são propostas (🤖 D1). `Repos` agrupa os repositórios para simplificar; a transação é única e é controlada pelo `CasoDeUso` (porta `UnidadeDeTrabalho`).

## 1. Realizar Pedido (UC-04)

Cobre: canal (`canalPedido`) obrigatório e validado (422), idempotência, transação única com reserva de estoque e `SELECT ... FOR UPDATE`, auditoria e outbox na mesma transação, caminho de 409 por saldo insuficiente (RN-05, RNF-11).

```mermaid
sequenceDiagram
    actor C as Cliente
    participant API as API (camada API)
    participant UC as CasoDeUso CriarPedido (aplicacao)
    participant D as Dominio (Pedido, Estoque)
    participant R as Repos (portas)
    participant AO as Auditoria e Outbox (portas)
    participant BD as PostgreSQL

    C->>API: POST /pedidos com canalPedido, itens e Idempotency-Key
    API->>API: valida JWT, perfil e schema
    alt token ausente, invalido ou expirado
        API-->>C: 401 erro padrao
    else perfil sem permissao ou unidade alheia
        API-->>C: 403 erro padrao
    else corpo JSON malformado
        API-->>C: 400 erro padrao
    else campo ausente ou canalPedido fora do enum APP TOTEM BALCAO PICKUP WEB
        API-->>C: 422 details field canalPedido
    else canalPedido incompativel com o perfil (RN-14)
        API-->>C: 422 details field canalPedido
    end
    API->>UC: executar(comando)
    UC->>R: reservar chave de idempotencia (chave, escopo, usuario, hash)
    R->>BD: INSERT em chaves_idempotencia ON CONFLICT
    alt chave ja concluida com o mesmo corpo
        BD-->>R: resposta guardada
        R-->>UC: estado repetido
        UC-->>API: resposta original sem novo pedido
        API-->>C: status e corpo originais
    else mesma chave com corpo diferente
        UC-->>API: erro de aplicacao
        API-->>C: 422 erro padrao
    else mesma chave ainda em processamento
        UC-->>API: erro de aplicacao
        API-->>C: 409 erro padrao
    else chave nova
        Note over UC,BD: inicio da transacao unica (RNF-11)
        UC->>R: itens do cardapio da unidade e precos
        R->>BD: SELECT em itens_cardapio e produtos
        BD-->>R: linhas
        R-->>UC: itens ofertaveis
        alt produto ou unidade inexistente
            UC-->>API: NotFoundError
            API-->>C: 404 erro padrao
        else produto indisponivel ou fora do periodo sazonal
            UC-->>API: erro de regra RN-12
            API-->>C: 422 erro padrao
        end
        UC->>D: Pedido.criar(unidade, itens, canal, criador, cliente)
        D-->>UC: pedido AGUARDANDO_PAGAMENTO com preco congelado e expiraEm
        UC->>R: obterParaAtualizar estoques em ordem de produto
        R->>BD: SELECT ... FOR UPDATE em estoques
        BD-->>R: linhas travadas
        loop para cada item do pedido
            UC->>D: Estoque.reservar(qtd, idPedido)
            alt saldo insuficiente
                D-->>UC: ESTOQUE_INSUFICIENTE
                UC->>BD: ROLLBACK (nada gravado)
                UC-->>API: erro de dominio
                API-->>C: 409 ESTOQUE_INSUFICIENTE
            else reservado
                D-->>UC: MovimentacaoEstoque RESERVA
            end
        end
        opt pedido informa pontos a resgatar (UC-10)
            UC->>R: obterParaAtualizar conta de pontos
            R->>BD: SELECT ... FOR UPDATE em saldos_pontos
            UC->>D: Pedido.aplicarResgate e ContaPontos.resgatar
            alt multiplo, limite de 50 por cento ou saldo invalidos
                D-->>UC: erro de dominio
                UC->>BD: ROLLBACK
                UC-->>API: erro
                API-->>C: 422 ou 409 erro padrao
            end
        end
        UC->>R: adicionar pedido, itens, historico e movimentacoes
        R->>BD: INSERT em pedidos, itens_pedido, historico_status_pedido e movimentacoes_estoque
        R->>BD: UPDATE em estoques
        UC->>AO: auditoria PEDIDO_CRIADO com canal, e eventos pedido_criado e estoque_movimentado
        AO->>BD: INSERT em auditoria e outbox_eventos
        UC->>R: guardar resposta da chave de idempotencia
        R->>BD: UPDATE em chaves_idempotencia
        UC->>BD: COMMIT
        UC-->>API: pedido criado
        API-->>C: 201 com pedido e canalPedido
    end
```

Pontos de atenção:

- **Quem decide o quê.** O 422 de `canalPedido` (ausente, fora do enum ou incompatível com o perfil, RN-14) sai da validação da API e do caso de uso antes de abrir transação alguma; o 400 é só para JSON malformado (D-054). O 409 sai do **domínio** (`Estoque.reservar`) e a API só o traduz.
- **Ordem do bloqueio.** As linhas de `estoques` são travadas em ordem determinística de produto para evitar *deadlock* entre dois pedidos concorrentes (DER, seção 4). A segunda transação concorrente espera o `COMMIT` ou o `ROLLBACK` da primeira e, então, lê o saldo atualizado.
- **Atomicidade.** Em qualquer falha (409, 422 de regra, erro de gravação), o `ROLLBACK` desfaz pedido, reserva, auditoria, outbox e a chave de idempotência (a chave só existe se o pedido existir).
- **Idempotência.** O retorno da mesma chave com o mesmo corpo devolve a resposta original sem nova reserva (RN-13); corpo diferente é 422 (DER 3.16); requisição concorrente ainda em processamento é 409 (RN-13, D-054).

## 2. Solicitar Pagamento (UC-05)

Cobre: aprovado (PAGO, baixa do estoque, acúmulo de pontos com consentimento), recusado (continua AGUARDANDO_PAGAMENTO), timeout com até 2 novas chamadas e 504 (RN-01, RN-06, RN-08, RNF-10).

```mermaid
sequenceDiagram
    actor C as Cliente
    participant API as API (camada API)
    participant UC as CasoDeUso SolicitarPagamento (aplicacao)
    participant D as Dominio (Pedido, Estoque, ContaPontos)
    participant R as Repos (portas)
    participant GW as Gateway mock (GatewayPagamento)
    participant AO as Auditoria e Outbox (portas)
    participant BD as PostgreSQL

    C->>API: POST /pedidos/{id}/pagamentos com forma, token de teste e Idempotency-Key
    API->>API: valida JWT e schema
    alt sem token valido
        API-->>C: 401 erro padrao
    else corpo JSON malformado
        API-->>C: 400 erro padrao
    else campo ausente ou forma de pagamento fora do enum
        API-->>C: 422 erro padrao
    end
    API->>UC: executar(comando)

    Note over UC,BD: transacao 1 curta, sem chamada externa dentro dela
    UC->>R: obter pedido e conferir titularidade
    R->>BD: SELECT em pedidos
    alt pedido inexistente ou de outro cliente
        UC-->>API: NotFoundError
        API-->>C: 404 erro padrao
    else colaborador de outra unidade
        UC-->>API: acesso negado
        API-->>C: 403 erro padrao
    end
    UC->>R: reservar chave de idempotencia
    alt chave repetida com o mesmo corpo
        UC-->>API: resposta original
        API-->>C: status e corpo originais sem nova cobranca
    else mesma chave com corpo diferente
        UC-->>API: erro de aplicacao
        API-->>C: 422 erro padrao
    end
    UC->>D: Pedido.solicitarPagamento(forma)
    alt pedido fora de AGUARDANDO_PAGAMENTO, expirado ou ja com cobranca efetivada
        D-->>UC: erro de regra
        UC-->>API: erro de dominio
        API-->>C: 409 erro padrao
    else tentativa PENDENTE criada
        D-->>UC: TentativaPagamento PENDENTE com valor do pedido
    end
    UC->>R: adicionar tentativa
    R->>BD: INSERT em tentativas_pagamento e COMMIT

    loop ate 3 chamadas: a primeira mais 2 novas, so por timeout (RNF-10)
        UC->>GW: solicitar pagamento (token, valor, chave) com timeout de 3 s
        alt tok_timeout: sem resposta em 3 s
            GW--xUC: timeout
            Note over UC: repete a chamada se ainda restam tentativas
        else resposta recebida
            GW-->>UC: aprovado ou recusado com payload
            Note over UC: sai do laco
        end
    end

    alt aprovado (tok_aprovado)
        Note over UC,BD: transacao 2
        UC->>R: obterParaAtualizar pedido, estoques e conta de pontos
        R->>BD: SELECT ... FOR UPDATE
        UC->>D: TentativaPagamento.aprovar e Pedido.confirmarPagamento
        D-->>UC: pedido PAGO, historico sem usuario
        loop para cada item
            UC->>D: Estoque.baixar(qtd, idPedido)
            D-->>UC: MovimentacaoEstoque BAIXA
        end
        UC->>R: consentimento vigente de FIDELIDADE
        R->>BD: SELECT do ultimo registro em consentimentos
        opt consentimento vigente CONCEDIDO (RN-08)
            UC->>D: ContaPontos.acumular(valor pago)
            D-->>UC: MovimentoPontos ACUMULO de 1 ponto por R$ 1,00
        end
        UC->>R: persistir tentativa, pedido, historico, estoques e pontos
        R->>BD: UPDATE e INSERT
        UC->>AO: auditoria e eventos pagamento_aprovado, estoque_movimentado e pontos_movimentados
        AO->>BD: INSERT em auditoria e outbox_eventos
        UC->>BD: COMMIT
        UC-->>API: tentativa APROVADO e pedido PAGO
        API-->>C: 201 com status PAGO
    else recusado (tok_recusado)
        Note over UC,BD: transacao 2
        UC->>D: TentativaPagamento.recusar(motivo)
        D-->>UC: pedido segue AGUARDANDO_PAGAMENTO, reserva mantida
        UC->>R: persistir tentativa RECUSADO com motivo
        R->>BD: UPDATE em tentativas_pagamento
        UC->>AO: auditoria e evento pagamento_recusado
        AO->>BD: INSERT em auditoria e outbox_eventos
        UC->>BD: COMMIT
        UC-->>API: tentativa RECUSADO
        API-->>C: 201 com status RECUSADO e motivo (pode tentar de novo)
    else timeout esgotado (tok_timeout)
        Note over UC,BD: transacao 2
        UC->>D: TentativaPagamento.falhar()
        D-->>UC: tentativa FALHA, pedido segue AGUARDANDO_PAGAMENTO
        UC->>R: persistir tentativa FALHA
        R->>BD: UPDATE em tentativas_pagamento
        UC->>AO: auditoria da falha do gateway
        UC->>BD: COMMIT
        UC-->>API: erro de dependencia
        API-->>C: 504 erro padrao apos cerca de 9 s
    end
```

Pontos de atenção:

- **Duas transações curtas.** A chamada ao gateway pode levar até cerca de 9 s no pior caso (3 chamadas de 3 s). Por isso ela acontece **fora** da transação, para não segurar bloqueios de linha de estoque e de pedido; o pedido fica em AGUARDANDO_PAGAMENTO nesse intervalo, e a tentativa PENDENTE o torna rastreável (🤖 D3).
- **Recusa mantém o pedido.** Recusa não repete automaticamente: só o timeout é repetido. Para tentar de novo, o cliente chama o endpoint outra vez (UC-20, RF-12), e a nova tentativa recebe o `numeroTentativa` seguinte (🤖 D4).
- **Idempotência da cobrança.** A chave vai também ao gateway; no banco, o índice único parcial de tentativa efetivada impede duas cobranças aprovadas no mesmo pedido (DER 3.11).
- **Pontos.** Sem consentimento vigente de FIDELIDADE, o bloco `opt` não ocorre e o pagamento termina normalmente (RN-08).
- **Registro das chamadas.** A quantidade de chamadas feitas ao gateway nessa tentativa (1 a 3) é gravada em `qtd_chamadas_gateway`, junto do resultado.
- **Fora de escopo do MVP.** O webhook assíncrono é evolução documentada; aqui o fluxo é síncrono (D-041).

## 3. Atualizar Status pela COZINHA (UC-06)

Cobre: transição válida (PAGO → EM_PREPARO → PRONTO), 403 por perfil ou unidade, 409 por transição inválida, 404 pedido inexistente, histórico, auditoria e outbox (RN-03, RN-04).

```mermaid
sequenceDiagram
    actor K as Cozinha
    participant API as API (camada API)
    participant UC as CasoDeUso AtualizarStatusPedido (aplicacao)
    participant D as Dominio (Pedido, PoliticaTransicao)
    participant R as Repos (portas)
    participant AO as Auditoria e Outbox (portas)
    participant BD as PostgreSQL

    K->>API: PATCH /pedidos/{id}/status com novo status
    API->>API: valida JWT e schema
    alt token ausente, invalido ou expirado
        API-->>K: 401 erro padrao
    else corpo JSON malformado
        API-->>K: 400 erro padrao
    else status ausente ou fora do enum
        API-->>K: 422 erro padrao
    end
    API->>UC: executar(comando com perfil e unidade do token)
    Note over UC,BD: transacao unica
    UC->>R: obterParaAtualizar pedido
    R->>BD: SELECT ... FOR UPDATE em pedidos
    alt pedido inexistente
        BD-->>R: nenhuma linha
        UC-->>API: NotFoundError
        API-->>K: 404 erro padrao
    end
    BD-->>R: pedido
    R-->>UC: Pedido
    UC->>D: PoliticaTransicao.perfilPodeTransitar(perfil, status atual, novo)
    D-->>UC: permitido ou negado
    UC->>UC: confere se a unidade do pedido e a de lotacao do usuario
    alt perfil nao autorizado para o status pedido ou pedido de outra unidade
        UC->>BD: ROLLBACK
        UC-->>API: acesso negado
        API-->>K: 403 erro padrao
    else autorizado
        UC->>D: Pedido.avancarStatus(novo, idAutor)
        alt transicao invalida (por exemplo PAGO para PRONTO, ou saida de ENTREGUE ou CANCELADO)
            D-->>UC: erro de dominio
            UC->>BD: ROLLBACK
            UC-->>API: erro de dominio
            API-->>K: 409 erro padrao
        else transicao valida
            D-->>UC: status atualizado e linha de historico
            UC->>R: persistir pedido e historico
            R->>BD: UPDATE em pedidos e INSERT em historico_status_pedido
            UC->>AO: auditoria STATUS_ALTERADO com canal e evento pedido_status_alterado
            AO->>BD: INSERT em auditoria e outbox_eventos
            UC->>BD: COMMIT
            UC-->>API: pedido atualizado
            API-->>K: 200 com o novo status
        end
    end
```

Pontos de atenção:

- **403 antes de 409.** A permissão (perfil e unidade) é checada antes da máquina de estados: quem não pode pedir aquele status recebe 403 mesmo que a transição fosse inválida. Exemplos: COZINHA pedindo ENTREGUE é 403; COZINHA pedindo PRONTO sobre um pedido PAGO (pulando EM_PREPARO) é permitido para o perfil, mas é 409 pela máquina de estados (🤖 D5).
- **PAGO nunca por aqui.** Pedir PAGO por qualquer perfil é 403 (RN-04), pois só o resultado do pagamento leva a PAGO.
- **Unidade.** COZINHA, ATENDENTE e GERENTE só atuam na unidade de lotação (RF-03); o ADMIN não faz transição de status. A mesma checagem vale no GERENTE de outra unidade.
- **Mesma estrutura para ATENDENTE.** PRONTO → ENTREGUE pelo ATENDENTE segue o mesmo diagrama, trocando o ator.

## Decisões da IA (pendentes de validação)

- 🤖 **D1.** Os valores de `error` (exceto `ESTOQUE_INSUFICIENTE`) e os nomes de eventos além dos já contratados (`pedido_criado`, `pagamento_aprovado`) são propostas.
- ✅ **D2.** Resolvida na D-054 (RN-13): chave em processamento é 409; corpo diferente é 422.
- ✅ **D3.** Adotada na D-054: pagamento em duas transações curtas, chamada ao gateway fora da transação.
- ✅ **D4.** Resolvida na D-054: uma linha de `tentativas_pagamento` por `POST` do cliente; as até 2 novas chamadas por timeout ficam dentro dela (`qtd_chamadas_gateway`).
- 🤖 **D5.** A permissão é decidida pelo status solicitado e pela unidade, antes da máquina de estados. Os requisitos não definem a ordem entre 403 e 409; propôs-se 403 primeiro.
- 🤖 **D6.** Recusa e criação respondem 201 (a tentativa é um recurso criado); a recusa é um resultado, não um erro. Resposta 504 só no timeout esgotado.
- 🤖 **D7.** Auditoria da falha de gateway (timeout esgotado) é registrada; os requisitos listam as ações auditáveis sem incluir esse caso.

---

*Redigido por Claude Sonnet 5.5 sob especificação do Claude Opus 5.5, a partir das decisões do humano registradas em `docs/uso-de-ia/decisoes.md`.*
