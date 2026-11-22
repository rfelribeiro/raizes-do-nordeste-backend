-- Gold: dimensão de unidade, MÍNIMA: só o id das unidades que aparecem nos eventos.
-- Lacuna: nome, cidade, uf, região e formato (da matriz) não existem nos eventos; exigem um evento
-- de cadastro de unidade. SCD 2 não implementado. A chave substituta segue a ordem de primeira
-- aparição (menor id_sequencial), estável porque o bronze só cresce.
with unidades as (

    select
        payload ->> 'unidade_id' as id_unidade,
        min(id_sequencial) as primeira_captura
    from {{ ref('stg_outbox_eventos') }}
    where tipo_agregado = 'pedido'
      and (payload ->> 'unidade_id') is not null
    group by 1

)

select cast(row_number() over (order by primeira_captura) as integer) as sk_unidade,
       cast(id_unidade as varchar) as id_unidade
from unidades
union all
select -1, cast(null as varchar)
