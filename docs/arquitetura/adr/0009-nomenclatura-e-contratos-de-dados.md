# ADR 0009 - Nomenclatura em inglês, dicionário de dados e contratos de dados

- **Status:** aceita; a nomenclatura em inglês foi substituída pelo [ADR 0010](0010-idioma-portugues.md) (dicionário e contratos seguem válidos)
- **Data:** 2026-11-14

> **Nomenclatura substituída pelo ADR-0010; dicionário e contratos seguem válidos.** O item 1 (nomes
> em inglês), o item 5 (`event_type` em inglês) e o item 6 (migração 0001 em inglês) abaixo ficam
> como registro histórico; os nomes vigentes são os do ADR 0010 (D-034).

## Contexto

O ADR 0008 propôs nomes de objetos de banco em português (`outbox_eventos`, `id_evento`,
`dim_tempo`). Essa proposta era da IA e nunca foi validada; o autor a rejeitou (D-023) e decidiu
(D-033) por nomes em inglês. O motivo é de longo prazo: a plataforma de dados deve **escalar** e
ter condições de receber **parcerias e integrações futuras** (fornecedores, outras redes,
ferramentas de BI, equipes externas), cujo vocabulário comum de engenharia de dados é o inglês.
Nomes técnicos em inglês só ajudam, porém, se vierem com um **dicionário de dados** que explique
cada objeto e com **contratos de dados** que tornem explícito o que o produtor promete ao
consumidor.

## Decisão

1. **Objetos de banco e de dados em inglês, `snake_case`:** tabelas, colunas, modelos dbt, seeds,
   campos dos eventos, variáveis de ambiente e módulos Python de infraestrutura e analytics.
   Prefixos `stg_`, `int_`, `dim_`, `fct_`; chaves `<entidade>_sk` (substituta) e
   `<entidade>_id` (natural); timestamps `*_at` (UTC); datas `*_date`; booleanos `is_*`/`has_*`;
   valores monetários `*_amount` (numeric(12,2), BRL); quantidades `*_qty`; durações
   `*_seconds`/`*_ms`; SCD2 com `valid_from`, `valid_to`, `is_current`; membros especiais -1
   (desconhecido / não se aplica) e -2 (anonimizado). Detalhes em
   [`docs/dados/dicionario-de-dados.md`](../../dados/dicionario-de-dados.md).
2. **Documentação continua em português** (nomes de arquivos `.md` inclusive), assim como os
   **valores** dos dados (ex.: feriado "Natal", mês "janeiro").
3. **Dicionário de dados** em `docs/dados/dicionario-de-dados.md`, com convenções, glossário de
   negócio pt → en e uma tabela por objeto implementado. O catálogo vivo é o `dbt docs`
   (`make dw-docs`); as descrições escritas nos YAMLs do dbt são a fonte de verdade dos objetos
   implementados.
4. **Contratos de dados** em `contracts/`, inspirados no Open Data Contract Standard (ODCS):
   JSON Schema do envelope do evento da outbox, contrato `outbox_events.contract.yaml` e testes
   automatizados (validação do envelope contra o schema; `contract: {enforced: true}` do dbt em
   `dim_date` e `stg_outbox_events`).
5. **Formato de `event_type`: `snake_case`** (ex.: `order_created`), no padrão
   `<entidade>_<fato_no_passado>`. É o formato que o domínio já deriva do nome da classe
   (`OrderCreated` -> `order_created`) e o mesmo dos demais nomes de objeto, o que evita uma
   segunda convenção. Alternativas descartadas: `PascalCase` (diverge do restante do banco) e
   `snake.dot` (ex.: `order.created`; agrega pouco e exigiria mudar o domínio).
6. **Migração 0001 substituída, sem migração de rename.** O banco nunca foi publicado nem
   implantado; existe apenas o ambiente local de desenvolvimento, com dados de teste. Empilhar uma
   migração de renomeação deixaria no histórico nomes em português que jamais existiram em
   produção. A migração 0001 foi reescrita com os nomes em inglês
   (`..._0001_create_outbox_events.py`) e o ambiente local foi recriado do zero (`make clean` e
   `make up`). **Isto só vale enquanto não houver ambiente implantado:** a partir da primeira
   implantação, toda mudança de nome passa a exigir uma migração incremental.

## Alternativas consideradas

- **Manter português (ADR 0008):** aproxima o vocabulário do negócio, mas dificulta integrações e
  parcerias; rejeitada pelo autor.
- **Misturar (tabelas em inglês, colunas em português):** incoerente; descartada.
- **Migração de renomeação sobre a 0001:** correta se o banco existisse fora do ambiente local;
  desnecessária aqui.
- **Contratos só em prosa:** não são verificáveis; preferiu-se esquema formal mais teste.

## Consequências

- (+) Vocabulário padronizado, pronto para integrações, parcerias e ferramentas externas.
- (+) Mudanças de formato dos eventos passam a ter regras de versionamento verificáveis
  (ver [`contracts/README.md`](../../../contracts/README.md)).
- (+) O dbt passa a recusar, na execução, modelos que fujam do tipo declarado (contrato imposto).
- (-) Termos do negócio precisam ser traduzidos; o glossário pt → en mitiga o risco.
- (-) Dados já gravados com nomes antigos (inexistentes além do ambiente local) foram descartados.
- (-) Manter dicionário e contratos exige disciplina; os testes e o dbt reduzem o risco de
  divergência.

**Autoria da decisão:** **humana.** O autor decidiu pelos nomes em inglês por escalabilidade e por
parcerias e integrações futuras. A IA propôs as convenções detalhadas, o dicionário e a estrutura
dos contratos; a implementação foi delegada a um agente subordinado, sob especificação.
