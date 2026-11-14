# Contratos de dados

Um **contrato de dados** é um acordo explícito e verificável entre quem **produz** um conjunto de
dados e quem o **consome**: o que os dados contêm, o que significam, com que qualidade e com que
frequência chegam, e como o formato pode mudar. Sem contrato, uma alteração inocente no produtor
quebra o consumidor sem aviso.

Referência: [Open Data Contract Standard (ODCS)](https://bitol-io.github.io/open-data-contract-standard/),
do projeto Bitol. Os contratos daqui seguem a mesma ideia, de forma simplificada e em português.
Nomes de campos e objetos estão em inglês (ADR 0009); o texto, em português.

## Partes de um contrato

| Parte | O que responde |
|---|---|
| Produtor | Quem gera os dados (ex.: a API `raizes`) |
| Consumidor | Quem depende dos dados (ex.: o DW) |
| Dono | Quem responde pelo contrato e aprova mudanças |
| Esquema | Campos, tipos e obrigatoriedade (formalizado em JSON Schema) |
| Semântica | O significado de cada campo e as regras de negócio |
| Qualidade | Verificações que os dados devem satisfazer (unicidade, ordem de datas etc.) |
| SLA de atualização | Quanto tempo, no máximo, o dado leva para chegar ao consumidor |
| Versionamento | Como o contrato evolui sem quebrar quem o usa |
| Privacidade | Restrições de LGPD (ex.: nenhum dado pessoal em claro) |

## Conteúdo

| Arquivo | Descrição |
|---|---|
| [`events/outbox_event_envelope.schema.json`](events/outbox_event_envelope.schema.json) | JSON Schema (draft 2020-12) do envelope do evento de domínio gravado na `outbox_events` |
| [`events/outbox_events.contract.yaml`](events/outbox_events.contract.yaml) | Contrato (estilo ODCS) da outbox: dono, produtor, consumidor, SLA, qualidade e privacidade |

## Regras de versionamento dos eventos

- O formato do `event_type` é `snake_case` no padrão `<entidade>_<fato_no_passado>`, em inglês
  (ex.: `order_created`). Um `event_type` já publicado **nunca é renomeado**.
- **Mudança aditiva** (novo campo opcional no `payload`): mantém o mesmo `event_type` e
  **incrementa `schema_version`**. Consumidores devem ignorar campos desconhecidos.
- **Mudança incompatível** (remover, renomear ou mudar o tipo ou o significado de um campo):
  exige **novo `event_type`** (ou nova versão maior combinada com os consumidores). Nunca se
  remove nem se renomeia campo sem novo major.
- O **envelope** (campos do evento fora do `payload`) segue as mesmas regras: qualquer mudança
  altera a versão do contrato e o JSON Schema.

## Regra de privacidade

O `payload` **não carrega dados pessoais em claro** (nome, CPF, e-mail, telefone, endereço, data
de nascimento). Usam-se identificadores internos e atributos derivados (ex.: faixa etária). O
bronze é imutável, então tudo o que entra num evento é, na prática, permanente
(ver [docs/dados/README.md](../docs/dados/README.md)).

## Como o contrato é verificado

- **Teste unitário** (`tests/unit/test_event_contract.py`): serializa um `DomainEvent` no formato
  da outbox e o valida contra o JSON Schema (`make test`).
- **dbt:** `dim_date` e `stg_outbox_events` têm `contract: {enforced: true}` com `data_type` em
  cada coluna; o `dbt build` falha se o modelo divergir do contrato (`make dw-build`).
- **Dicionário:** descrições e tipos em [`docs/dados/dicionario-de-dados.md`](../docs/dados/dicionario-de-dados.md).
