-- Gold: dimensão de status do pedido (SCD 1, estática). Valores do enum OrderStatus.
select cast(sk_status_pedido as integer) as sk_status_pedido,
       cast(nome_status_pedido as varchar) as nome_status_pedido,
       cast(ordem_fluxo as integer) as ordem_fluxo,
       cast(eh_final as boolean) as eh_final
from (values
    (-1, 'NÃO IDENTIFICADO', cast(null as integer), false),
    (1, 'AGUARDANDO_PAGAMENTO', 1, false),
    (2, 'PAGO', 2, false),
    (3, 'EM_PREPARO', 3, false),
    (4, 'PRONTO', 4, false),
    (5, 'ENTREGUE', 5, true),
    (6, 'CANCELADO', 6, true)
) as t(sk_status_pedido, nome_status_pedido, ordem_fluxo, eh_final)
