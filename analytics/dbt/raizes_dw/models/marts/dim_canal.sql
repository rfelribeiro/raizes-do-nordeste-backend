-- Gold: dimensão de canal (SCD 1, estática). Valores do enum OrderChannel (canalPedido do roteiro).
select cast(sk_canal as integer) as sk_canal,
       cast(nome_canal as varchar) as nome_canal,
       cast(tipo_canal as varchar) as tipo_canal
from (values
    (-1, 'NÃO IDENTIFICADO', 'não identificado'),
    (1, 'APP', 'digital'),
    (2, 'TOTEM', 'presencial'),
    (3, 'BALCAO', 'presencial'),
    (4, 'PICKUP', 'digital'),
    (5, 'WEB', 'digital')
) as t(sk_canal, nome_canal, tipo_canal)
