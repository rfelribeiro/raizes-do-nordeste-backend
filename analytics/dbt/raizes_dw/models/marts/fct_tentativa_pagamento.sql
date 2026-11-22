-- Gold: fato de tentativa de pagamento. Grão: uma tentativa com resultado (aprovada ou recusada).
-- Lacunas: latencia_gateway_ms e tentativas com timeout (a tentativa FALHA não gera evento).
with eventos as (

    select * from {{ ref('stg_outbox_eventos') }} where tipo_agregado = 'pedido'

),

pedido as (

    select id_agregado as id_pedido, payload ->> 'cliente_id' as id_cliente
    from eventos
    where tipo_evento = 'pedido_criado'

),

tentativa as (

    select
        id_agregado as id_pedido,
        cast(payload ->> 'numero_tentativa' as integer) as numero_tentativa,
        case tipo_evento when 'pagamento_aprovado' then 'APROVADO' else 'RECUSADO' end as resultado,
        payload ->> 'motivo' as motivo_recusa,
        ocorrido_em,
        cast(ocorrido_em at time zone 'America/Recife' as timestamp) as ocorrido_local,
        payload ->> 'unidade_id' as id_unidade,
        payload ->> 'canal_pedido' as nome_canal,
        payload ->> 'forma_pagamento' as nome_forma_pagamento,
        cast(payload ->> 'valor' as decimal(12, 2)) as valor
    from eventos
    where tipo_evento in ('pagamento_aprovado', 'pagamento_recusado')

)

select
    t.id_pedido,
    t.numero_tentativa,
    cast(t.resultado as varchar) as resultado,
    t.motivo_recusa,
    cast(strftime(t.ocorrido_local, '%Y%m%d') as integer) as sk_data,
    cast(hour(t.ocorrido_local) * 100 + minute(t.ocorrido_local) as integer) as sk_hora,
    coalesce(u.sk_unidade, -1) as sk_unidade,
    coalesce(ca.sk_canal, -1) as sk_canal,
    coalesce(f.sk_forma_pagamento, -1) as sk_forma_pagamento,
    coalesce(cl.sk_cliente, -1) as sk_cliente,
    t.valor as valor_solicitado,
    cast(case when t.resultado = 'APROVADO' then t.valor else 0 end as decimal(12, 2)) as valor_aprovado,
    t.ocorrido_em
from tentativa as t
left join pedido as p on p.id_pedido = t.id_pedido
left join {{ ref('dim_unidade') }} as u on u.id_unidade = t.id_unidade
left join {{ ref('dim_canal') }} as ca on ca.nome_canal = t.nome_canal
left join {{ ref('dim_forma_pagamento') }} as f on f.nome_forma_pagamento = t.nome_forma_pagamento
left join {{ ref('int_cliente_pseudonimo') }} as cl on cl.id_cliente = p.id_cliente
