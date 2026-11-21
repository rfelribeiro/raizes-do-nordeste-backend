# ADR 0010 - Tudo em português: API, banco, DW e eventos

- **Status:** aceita (substitui a nomenclatura do [ADR 0009](0009-nomenclatura-e-contratos-de-dados.md))
- **Data:** 2026-11-14

## Contexto

O [ADR 0009](0009-nomenclatura-e-contratos-de-dados.md) (D-033) decidiu por nomes de dados em
inglês, pensando em parcerias e integrações futuras. Depois disso, o roteiro oficial da trilha
(PDF oficial da disciplina, mantido só localmente; ver D-055) mostrou que o
**contrato da API é em português**: rotas (`/pedidos`, `/unidades`), campos (`canalPedido`,
`clienteId`, `itens`, `quantidade`), enums (`APP`, `TOTEM`, `BALCAO`, `PICKUP`, `WEB`) e mensagens
de erro. Manter a API em português e o banco em inglês criaria duas línguas no mesmo sistema.

A IA recomendou **API em português e dados (banco, DW, eventos) em inglês**, para preservar a
vantagem de integração com o vocabulário internacional de dados. O humano escolheu **tudo em
português**.

## Decisão

1. **Tudo em português, `snake_case` sem acento:** contrato da API (rotas no plural, campos JSON em
   `camelCase`, enums em MAIÚSCULAS sem acento) e objetos de banco, DW e eventos (tabelas, colunas,
   modelos dbt, seeds, `tipo_evento`, caminhos do lake). Convenções completas (prefixos `stg_`,
   `int_`, `dim_`, `fct_`; `sk_<entidade>`, `id_<entidade>`; `*_em`, `data_*`, `eh_*`/`tem_*`,
   `valor_*`, `qtd_*`, `duracao_*_s`; SCD2 `valido_de`, `valido_ate`, `eh_atual`; membros -1 e -2)
   no [dicionário de dados](../../dados/dicionario-de-dados.md).
2. **Mantém o dicionário de dados e os contratos de dados** do ADR 0009. O glossário do dicionário
   passa a ser uma **ponte português -> inglês** para integrações e parcerias.
3. **Exceções, em inglês:** identificadores de código Python (classes, funções, variáveis,
   atributos) e variáveis de ambiente (convenção operacional; as `POSTGRES_*` são fixas das
   imagens oficiais). Exemplo: o atributo `OutboxEvent.event_type` é mapeado para a coluna
   `tipo_evento`.
4. **`tipo_evento`** em `snake_case` português no padrão `<entidade>_<particípio>` (ex.:
   `pedido_criado`, `pagamento_aprovado`). Como as classes de evento são em inglês, cada evento
   declara `event_type` explicitamente como atributo de classe.
5. **Canal:** o enum `canalPedido` do roteiro (`APP`, `TOTEM`, `BALCAO`, `PICKUP`, `WEB`) vale na
   API e em `dim_canal`; o canal `WEB` foi acrescentado à matriz de barramento.
6. **Migração 0001 reescrita, sem migração de rename**, pelo mesmo motivo do ADR 0009: o banco
   nunca foi publicado, existe só o ambiente local (recriado com `make clean` e `make up`). A
   partir da primeira implantação, toda mudança de nome exige migração incremental.

## Alternativas consideradas

- **API em português e dados em inglês (recomendação da IA):** preserva o vocabulário internacional
  de engenharia de dados, mas mantém duas línguas no sistema e exige tradução constante entre a
  API e o DW. Não escolhida pelo humano.
- **Tudo em inglês:** contradiz o contrato exigido pelo roteiro.
- **Dicionário apenas em português, sem a ponte:** perderia o ganho de integração; a ponte
  pt -> en custa pouco.

## Consequências

- (+) Uma única língua entre API, banco e DW; o vocabulário do negócio é o mesmo do roteiro.
- (+) Aderência direta ao contrato exigido pela avaliação.
- (-) Integrações externas dependem da ponte pt -> en do dicionário.
- (-) Há duas convenções por fronteira (código e variáveis de ambiente em inglês; dados em
  português), documentadas aqui e no dicionário.
- (-) Reescrever a migração 0001 só é válido enquanto não houver ambiente implantado.

**Autoria da decisão:** **humana.** A IA recomendou API em português e dados em inglês; o humano
escolheu tudo em português (D-034). A implementação foi delegada a um agente subordinado, sob
especificação.
