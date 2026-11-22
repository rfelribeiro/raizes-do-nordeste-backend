-- Grão do fato: (id_pedido, numero_tentativa) deve ser único. Retorna as linhas que violam.
select id_pedido, numero_tentativa, count(*) as qtd
from {{ ref('fct_tentativa_pagamento') }}
group by id_pedido, numero_tentativa
having count(*) > 1
