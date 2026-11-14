# Matriz de barramento e modelagem dimensional

**Autoria:** o **autor (humano)** escolheu os processos de negócio, as dimensões, os grãos e as interseções da matriz, numa sessão guiada em que a IA apresentou opções com o conceito de cada uma. A pedido do autor ("defina de acordo com boas práticas de mercado"), a **IA** definiu as dimensões dos consentimentos, as estratégias de SCD, os membros especiais, o tratamento sazonal e as medidas. Cada seção indica a origem com a legenda de [`docs/uso-de-ia`](../uso-de-ia/README.md#legenda-de-origem). Registro: decisões D-028 a D-032 em [`decisoes.md`](../uso-de-ia/decisoes.md). **Nomenclatura:** os nomes técnicos dos objetos estão em português (D-034, [ADR-0010](../arquitetura/adr/0010-idioma-portugues.md), que substitui a nomenclatura em inglês da D-033/[ADR-0009](../arquitetura/adr/0009-nomenclatura-e-contratos-de-dados.md)); o conteúdo conceitual e a autoria permanecem os mesmos (único acréscimo: o canal `WEB`, exigido pelo enum `canalPedido` do roteiro da trilha). Os cabeçalhos da matriz abaixo ficam em português por serem texto; a correspondência com as tabelas está na seção de dimensões.

## Método

A modelagem segue os **4 passos do projeto dimensional de Kimball**, nesta ordem:

1. **Escolher o processo de negócio**, ou seja, um evento mensurável que vira uma tabela fato.
2. **Declarar o grão**: o que exatamente uma linha do fato representa. O grão vem *antes* das dimensões porque define quais delas cabem. Por exemplo, um saldo **diário** não comporta a dimensão Hora.
3. **Identificar as dimensões**: o contexto do evento (quem, o quê, onde, quando, como, por quê).
4. **Identificar as medidas**: os números, sempre coerentes com o grão.

A **matriz de barramento** cruza processos e dimensões. Ela torna visível quais dimensões são **conformadas**, isto é, compartilhadas com as mesmas chaves e o mesmo significado. É isso que permite cruzar fatos diferentes, como vendas × estoque × fidelidade, e construir o DW de forma incremental, um processo por vez.

## Referência rápida (glossário)

- **Grão:** o que uma linha da tabela fato representa (ex.: "uma linha por item de pedido").
- **Fato transacional:** uma linha por evento, no instante em que ele ocorre. Só cresce.
- **Fato snapshot periódico:** uma linha por entidade a cada período fixo (ex.: saldo diário). Mede estados, inclusive nos períodos em que nada aconteceu.
- **Fato snapshot acumulativo:** uma linha por ciclo de vida, com marcos (datas) atualizados conforme o processo avança.
- **Fato sem medida (factless):** registra que algo aconteceu ou vigora, sem valor numérico. Analisa-se por contagem.
- **Dimensão conformada:** a mesma dimensão, com as mesmas chaves, em todos os processos que a usam.
- **Dimensão degenerada:** identificador operacional (ex.: número do pedido) guardado no próprio fato, sem tabela de dimensão.
- **Dimensão role-playing:** uma única dimensão física usada várias vezes no mesmo fato, cada vez com um papel (data de criação, data de pagamento...).
- **SCD (dimensão que muda lentamente):** tipo 0 = nunca muda; tipo 1 = sobrescreve, sem histórico; tipo 2 = nova linha por mudança, com vigência e histórico completo. **Decide-se por atributo, não por tabela.**
- **Aditividade das medidas:** *aditiva* soma em qualquer dimensão; *semi-aditiva* soma em algumas mas não no tempo (ex.: saldo); *não aditiva* nunca soma (ex.: preço unitário, percentuais).

## Insumos do estudo de caso

Citações literais de `init/roteiro.md` relevantes para análise (número da linha entre parênteses).

| Tema | Citação | Linha |
|---|---|---|
| Vendas por unidade e região | "vendas por unidade e por região;" | 106 |
| Produtos mais consumidos | "produtos mais consumidos;" | 107 |
| Relatórios financeiros | "relatórios financeiros;" | 108 |
| Consolidação estratégica | "dados consolidados para decisões estratégicas;" | 109 |
| Auditoria de operações sensíveis | "auditoria de operações sensíveis (cancelamentos, descontos, ajustes)." | 110 |
| Múltiplos canais | "Aplicativo oficial (pedidos antecipados, promoções, fidelização);" / "Totens de auto-atendimento nas lojas;" / "Atendimento humano no balcão;" / "Pedidos para retirada rápida (pick-up)." | 76 a 79 |
| Unidades com formatos diferentes | "Algumas possuem cozinha completa, outras operam em formato reduzido." | 91 |
| Produtos sazonais / juninos | "Certos produtos só estão disponíveis em épocas específicas do ano (especialmente no período junino)" | 91 |
| Variações regionais | "algumas receitas variam levemente conforme a região." | 91 |
| Estoque local | "controle de estoque local;" | 100 |
| Metas e indicadores por unidade | "metas e indicadores de desempenho." | 102 |
| Fidelidade: pontos | "acumular pontos;" | 118 |
| Fidelidade: campanhas segmentadas | "permitir campanhas segmentadas;" | 120 |
| Fidelidade: frequência, idade e perfil | "considerar fatores como frequência de consumo, idade e perfil do cliente." | 121 |
| Consentimento | "consentimento explícito para uso de dados;" | 129 |
| Anonimização | "anonimização quando aplicável;" | 134 |
| Auditoria de acessos | "auditoria de acessos;" | 135 |
| Pagamento externo: solicitação | "solicita o pagamento;" | 144 |
| Pagamento externo: confirmação ou negativa | "recebe a confirmação ou negativa;" | 145 |
| Pagamento externo: registro e status | "registra o resultado;" / "atualiza o status do pedido." | 146, 147 |
| Rastreabilidade | "A franqueadora exige padronização, rastreabilidade e transparência" | 112 |

## Processos de negócio e grãos — 🧑 autor

| # | Processo | Tabela fato | Tipo | Grão (uma linha representa...) |
|---|---|---|---|---|
| 1 | Itens de pedido | `fct_item_pedido` | Transacional | um item (produto) dentro de um pedido |
| 2 | Pedidos | `fct_pedido` | Transacional | um pedido no estado final |
| 3 | Ciclo de vida do pedido | `fct_ciclo_pedido` | Snapshot acumulativo | um pedido, com os marcos atualizados a cada etapa |
| 4 | Pagamentos | `fct_tentativa_pagamento` | Transacional | uma tentativa de pagamento no gateway externo, com o resultado |
| 5 | Movimentação de estoque | `fct_movimentacao_estoque` | Transacional | um movimento de um produto numa unidade (entrada, venda, perda, ajuste) |
| 6 | Saldo de estoque | `fct_saldo_estoque_diario` | Snapshot periódico | produto × unidade × dia (saldo no fechamento) |
| 7 | Fidelidade | `fct_movimento_pontos` | Transacional | um movimento de pontos de um cliente (acúmulo, resgate, expiração, estorno) |
| 8 | Operações sensíveis | `fct_operacao_sensivel` | Transacional | um cancelamento, desconto ou ajuste |
| 9 | Consentimentos LGPD | `fct_consentimento_diario` | Snapshot periódico sem medida | cliente × finalidade × dia, com o status vigente |

Pontos conceituais destas escolhas:

- O fato 1 é o **grão atômico** das vendas. O fato 2 existe porque há medidas que só fazem sentido no cabeçalho, como o desconto global. Ratear essas medidas nos itens seria artificial.
- **Estoque** usa dois fatos complementares sobre o mesmo assunto. O transacional explica *por que* o saldo mudou; o snapshot mostra *quanto* havia, inclusive nos dias sem movimento.
- **Pagamentos por tentativa** preservam negativas e falhas do gateway, que são evidência de tolerância a falhas na integração externa.
- O **ciclo de vida** é o único fato que sofre atualização (*upsert*), característica própria do snapshot acumulativo. Ele mede os tempos de atendimento no horário de pico.

## Matriz de barramento — 🧑 autor (dimensão Finalidade: 🤖 IA)

Legenda: **X** = dimensão presente · **RP** = role-playing (várias datas com papéis diferentes) · **D** = número do pedido (`numero_pedido`) como dimensão degenerada.

| Processo | Tempo | Hora | Unidade | Produto | Canal | Cliente | Forma pgto | Campanha | Colaborador | Status | Motivo | Finalidade | Nº pedido (`numero_pedido`) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1. Itens de pedido | X | X | X | X | X | X | | X | | | | | D |
| 2. Pedidos | X | X | X | | X | X | | X | X | X | | | D |
| 3. Ciclo de vida do pedido | RP | | X | | X | | | | | X | | | D |
| 4. Pagamentos | X | X | X | | X | X | X | | | | X | | D |
| 5. Movimentação de estoque | X | X | X | X | | | | | X | | X | | |
| 6. Saldo de estoque diário | X | | X | X | | | | | | | | | |
| 7. Fidelidade (pontos) | X | | X | | X | X | | X | | | X | | |
| 8. Operações sensíveis | X | X | X | X | X | | | X | X | | X | | D |
| 9. Consentimentos LGPD | X | | | | X | X | | | | | | X | |

Correspondência dos cabeçalhos com as tabelas: Tempo = `dim_tempo`, Hora = `dim_hora`, Unidade = `dim_unidade`, Produto = `dim_produto`, Canal = `dim_canal`, Cliente = `dim_cliente`, Forma pgto = `dim_forma_pagamento`, Campanha = `dim_campanha`, Colaborador = `dim_colaborador`, Status = `dim_status_pedido`, Motivo = `dim_motivo`, Finalidade = `dim_finalidade`.

**Dimensões conformadas** (aparecem em 3 ou mais processos): Tempo, Unidade, Canal, Cliente, Produto, Hora, Campanha, Motivo e Colaborador. Elas precisam ser construídas uma única vez e reutilizadas por todos os fatos.

A **dimensão Finalidade** não estava na lista inicial. A IA a acrescentou porque o grão escolhido para os consentimentos ("por finalidade") não fecha sem ela.

## Dimensões e SCD — 🤖 IA (boas práticas, a pedido do autor)

| Dimensão | Principais atributos | SCD | Justificativa |
|---|---|---|---|
| `dim_tempo` | `data`, `ano`, `trimestre`, `mes`, `dia_semana`, `nome_feriado`, `eh_periodo_junino` | 0 | O calendário não muda. É gerada (date spine), e não extraída. |
| `dim_hora` | `hora`, `minuto`, `periodo_dia` (café da manhã, almoço, tarde, noite), `eh_pico` | 0 | Separar hora de data evita multiplicar a `dim_tempo` por 1.440 minutos. |
| `dim_unidade` | `nome_unidade`, `cidade`, `uf`, `regiao`, **`formato_unidade`** (cozinha completa ou reduzida), `data_abertura` | **2** em formato, região e status; **1** em nome | Uma reforma de formato precisa preservar o formato antigo nas vendas antigas, para comparar antes e depois. |
| `dim_produto` | `nome_produto`, `descricao`, `categoria`, **`eh_sazonal`**, `temporada`, `variante_regional` | **2** em categoria, sazonalidade e variante; **1** em nome e descrição (correções) | Correção de digitação não deve gerar versão. O **preço não fica na dimensão**: o preço praticado é medida do fato. |
| `dim_canal` | `nome_canal` (`APP`, `TOTEM`, `BALCAO`, `PICKUP`, `WEB`; valores do enum `canalPedido` do roteiro da trilha), `tipo_canal` (digital ou presencial) | 1 | Lista pequena de referência. |
| `dim_cliente` | `id_cliente` pseudonimizado (HMAC), `faixa_etaria`, `perfil_consumo`, `cidade`, `uf`, `data_adesao_fidelidade` | **2** em faixa etária e perfil; **1** em flag de consentimento vigente | Segmentar pelo perfil que o cliente tinha na data da compra. **Sem nome, CPF, e-mail ou telefone.** |
| `dim_forma_pagamento` | `nome_forma_pagamento` (pix, crédito, débito, vale-refeição, pontos), `grupo_forma_pagamento` | 1 | Lista de referência. |
| `dim_campanha` | `nome_campanha`, `tipo_campanha` (desconto, pontos bônus), `segmento_alvo`, `data_inicio`, `data_fim` | 1 | Uma campanha não muda depois de lançada; ajustes são correções. |
| `dim_colaborador` | `id_colaborador` pseudonimizado, **`papel`** (atendente, cozinheiro, gerente), `id_unidade_lotacao` (unidade de lotação) | **2** em papel e lotação | A auditoria precisa saber o papel e a lotação **na data da operação**. Sem dados pessoais. |
| `dim_status_pedido` | `nome_status_pedido`, `ordem_fluxo`, `eh_final` | 1 | Lista de referência. |
| `dim_motivo` | `nome_motivo`, `tipo_motivo` (cancelamento, desconto, ajuste de estoque, perda, negativa de pagamento, movimento de pontos), `exige_aprovacao` | 1 | Padroniza o texto livre em categorias auditáveis. Uma única dimensão com atributo de tipo evita várias minidimensões. |
| `dim_finalidade` | `nome_finalidade` (marketing, campanhas segmentadas, análise de perfil, comunicação transacional), **`base_legal`** (base legal LGPD) | 1 | Liga cada uso de dado à base legal correspondente. |

Convenções de SCD tipo 2: colunas `valido_de`, `valido_ate` (9999-12-31 na versão vigente) e `eh_atual`, e chave substituta por versão (`sk_<entidade>`), diferente da chave natural (`id_<entidade>`). Convenções completas em [`dicionario-de-dados.md`](dicionario-de-dados.md). No dbt, a implementação usa **snapshots** (estratégia `check` sobre os atributos versionados).

### Membros especiais

| Chave | Significado | Uso |
|---|---|---|
| -1 | Não identificado / não se aplica | Pedido sem cliente cadastrado ou sem consentimento (decisão do autor); colaborador em pedidos do app e do totem; produto em operação sobre o pedido inteiro; unidade na expiração de pontos |
| -2 | Anonimizado | Cliente que exerceu o direito de eliminação (LGPD): **todas** as versões dele são reapontadas para -2, o que preserva os totais e elimina a identificação |

As chaves estrangeiras dos fatos **nunca são nulas**: uma ausência aponta para -1. Assim, o join interno não perde linhas e o "desconhecido" aparece explicitamente nos relatórios.

## Medidas — 🤖 IA (boas práticas, a pedido do autor)

| Fato | Medidas | Aditividade |
|---|---|---|
| `fct_item_pedido` | `qtd_vendida`, `valor_bruto`, `valor_desconto`, `valor_liquido` | aditivas |
| | `valor_preco_unitario` | não aditiva (média ponderada pela quantidade) |
| `fct_pedido` | `valor_bruto`, `valor_desconto`, `valor_liquido`, `qtd_itens` | aditivas (o ticket médio é derivado: valor_liquido ÷ nº de pedidos) |
| `fct_ciclo_pedido` | marcos (`sk_data_*` e `*_em`): criado, pago, em preparo, pronto, entregue, cancelado; `duracao_espera_pagamento_s`, `duracao_preparo_s`, `duracao_total_s` | durações: aditivas, analisadas por média e percentis (p50/p95) |
| `fct_tentativa_pagamento` | `valor_solicitado`, `valor_aprovado` | aditivas |
| | `latencia_gateway_ms`; `resultado` (aprovado, negado, erro, timeout) como atributo degenerado | latência não aditiva (percentis) |
| `fct_movimentacao_estoque` | `qtd_movimento` (com sinal: + entrada, − saída) | aditiva |
| `fct_saldo_estoque_diario` | `qtd_saldo`, `qtd_minima`, `eh_ruptura` | **semi-aditivas**: somam entre produtos e unidades, mas **não** ao longo dos dias (usa-se o último valor ou a média) |
| `fct_movimento_pontos` | `pontos` (com sinal) | aditiva (saldo do cliente = soma) |
| `fct_operacao_sensivel` | `valor_impactado` | aditiva (a contagem de operações = nº de linhas) |
| `fct_consentimento_diario` | `eh_consentido` | sem medida (factless); analisa-se por contagem |

## Cliente não identificado — 🧑 autor

Pedidos sem cliente cadastrado, ou de cliente sem consentimento para uso analítico, apontam para o **membro -1 "Não identificado"**. Eles continuam contando em vendas, canal, produto e unidade, mas nunca alimentam segmentação nem fidelidade. Um cliente que pede a eliminação dos dados passa para o membro **-2 "Anonimizado"** (ver Membros especiais).

## Atributos sazonais — 🤖 IA (boas práticas, a pedido do autor)

- **No produto:** `eh_sazonal` e `temporada` (ex.: "junina") são atributos SCD tipo 2 da `dim_produto`. A disponibilidade do produto por unidade e período pertence ao OLTP (cardápio); o DW registra o que foi vendido.
- **No calendário:** `eh_periodo_junino` fica na `dim_tempo`, e não no produto. O período é uma propriedade da data e vale para todos os fatos, permitindo comparar vendas, estoque e fidelidade dentro e fora do período.
- **Definição do período:** um calendário comercial governado pela área de negócio (seed `calendario_comercial`) é a prática recomendada, em vez de uma regra fixa no código. O padrão provisório continua sendo de 01/06 a 31/07 (São João em 24/06, São Pedro em 29/06 e festejos que se estendem por julho em várias praças), parametrizado em `dbt_project.yml`.
