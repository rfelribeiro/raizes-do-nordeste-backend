-- Gold: fato de pedido. Grão: um pedido, no status mais recente conhecido.
-- Datas/horas na data civil e hora local de America/Recife (ver dim_tempo).
-- Lacunas (não existem nos eventos): numero_pedido, campanha, colaborador, qtd_itens, desconto real.
with eventos as (

    select * from {{ ref('stg_outbox_eventos') }} where tipo_agregado = 'pedido'

),

criado as (

    select
        id_agregado as id_pedido,
        ocorrido_em as criado_em,
        cast(ocorrido_em at time zone 'America/Recife' as timestamp) as criado_local,
        payload ->> 'unidade_id' as id_unidade,
        payload ->> 'cliente_id' as id_cliente,
        payload ->> 'canal_pedido' as nome_canal,
        payload ->> 'status' as status_inicial,
        cast(payload ->> 'valor_total' as decimal(12, 2)) as valor_bruto
    from eventos
    where tipo_evento = 'pedido_criado'

),

ultimo_status as (

    select id_agregado as id_pedido, payload ->> 'status_novo' as status_novo
    from eventos
    where tipo_evento = 'status_pedido_alterado'
    qualify row_number() over (partition by id_agregado order by ocorrido_em desc, id_sequencial desc) = 1

)

select
    c.id_pedido,
    cast(strftime(c.criado_local, '%Y%m%d') as integer) as sk_data,
    cast(hour(c.criado_local) * 100 + minute(c.criado_local) as integer) as sk_hora,
    coalesce(u.sk_unidade, -1) as sk_unidade,
    coalesce(ca.sk_canal, -1) as sk_canal,
    coalesce(cl.sk_cliente, -1) as sk_cliente,
    coalesce(s.sk_status_pedido, -1) as sk_status_pedido,
    c.valor_bruto,
    cast(0 as decimal(12, 2)) as valor_desconto,
    c.valor_bruto as valor_liquido,
    c.criado_em
from criado as c
left join ultimo_status as us on us.id_pedido = c.id_pedido
left join {{ ref('dim_unidade') }} as u on u.id_unidade = c.id_unidade
left join {{ ref('dim_canal') }} as ca on ca.nome_canal = c.nome_canal
left join {{ ref('int_cliente_pseudonimo') }} as cl on cl.id_cliente = c.id_cliente
left join {{ ref('dim_status_pedido') }} as s on s.nome_status_pedido = coalesce(us.status_novo, c.status_inicial)
