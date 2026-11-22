-- Gold: dimensão de cliente, MÍNIMA e pseudonimizada. O id em claro NÃO sai aqui: só o HMAC-SHA256
-- (calculado em int_cliente_pseudonimo). Membros: -1 sem cliente; -2 anonimizado (só o membro;
-- o processo de anonimização, que reaponta os fatos para -2, fica como evolução).
-- Lacunas: faixa etária, perfil, cidade, uf e data de adesão não existem nos eventos; SCD 2 não implementado.
select cast(sk_cliente as integer) as sk_cliente,
       cast(id_cliente_pseudonimo as varchar) as id_cliente_pseudonimo,
       cast('identificado' as varchar) as situacao_cliente
from {{ ref('int_cliente_pseudonimo') }}
union all
select -1, cast(null as varchar), 'não identificado'
union all
select -2, cast(null as varchar), 'anonimizado'
