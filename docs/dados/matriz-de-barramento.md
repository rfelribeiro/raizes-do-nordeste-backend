# Matriz de barramento e modelagem dimensional

**Documento de autoria humana. A IA forneceu apenas a estrutura e os insumos do estudo de caso.**

Os processos de negócio, as dimensões, os grãos, os tipos de fato e as estratégias de SCD são
decisões do autor. Nada abaixo foi preenchido ou sugerido pela IA, exceto o glossário e os
trechos citados do estudo de caso.

## Referência rápida (glossário)

- **Matriz de barramento (bus matrix):** tabela com os **processos de negócio** nas linhas e as
  **dimensões** nas colunas; a marca na interseção diz que aquele processo usa aquela dimensão.
  Planeja o DW de forma incremental e garante dimensões compartilhadas entre processos.
- **Grão:** o que representa exatamente uma linha da tabela fato (ex.: "uma linha por item de
  pedido"). É a primeira decisão de cada fato; tudo (medidas, dimensões) deve ser coerente com ele.
- **Fato transacional:** uma linha por evento no instante em que ocorre; só cresce, não é atualizada.
- **Fato snapshot periódico:** uma linha por entidade a cada período fixo (ex.: saldo diário); mede
  estados, inclusive quando nada aconteceu.
- **Fato snapshot acumulativo:** uma linha por ciclo de vida de um processo com marcos (datas) que
  são preenchidos e atualizados conforme o processo avança.
- **Dimensão conformada:** dimensão com o mesmo significado e chaves em todos os processos que a
  usam (ex.: uma única dimensão de tempo para tudo), o que permite cruzar fatos diferentes.
- **SCD (dimensão que muda lentamente):** tipo 0 = valor nunca muda (mantém o original); tipo 1 =
  sobrescreve (sem histórico); tipo 2 = nova linha por mudança, com vigência (histórico completo).

Já existe uma dimensão de tempo genérica (`dim_tempo`, ver [README](README.md)). As demais são do autor.

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

## Matriz de barramento (a preencher pelo autor)

Marque as interseções (ex.: com "X"). Acrescente linhas e colunas conforme necessário.

| Processo de negócio (a definir) | Dimensão (a definir) | Dimensão (a definir) | Dimensão (a definir) | Dimensão (a definir) | Dimensão (a definir) |
|---|---|---|---|---|---|
| Processo de negócio (a definir) | | | | | |
| Processo de negócio (a definir) | | | | | |
| Processo de negócio (a definir) | | | | | |
| Processo de negócio (a definir) | | | | | |

## Decisões do autor

Campos em branco, a serem preenchidos pelo autor.

### Grão de cada fato

| Fato | Grão (uma linha representa...) |
|---|---|
| | |

### Tipo de cada fato (transacional, snapshot periódico ou acumulativo)

| Fato | Tipo | Justificativa |
|---|---|---|
| | | |

### SCD de cada dimensão (tipo 0, 1 ou 2)

| Dimensão | Tipo de SCD | Atributos afetados | Justificativa |
|---|---|---|---|
| | | | |

### Cliente não identificado

Como tratar pedidos sem cliente cadastrado ou sem consentimento (membro -1? agregado anônimo?):

> _(a preencher)_

### Atributos sazonais

Como representar produtos sazonais/juninos e o que define o período junino (hoje, parâmetro
provisório em `dbt_project.yml`):

> _(a preencher)_
