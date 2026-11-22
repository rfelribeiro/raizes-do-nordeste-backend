-- Gold: dimensão de hora do dia, grão minuto (1440 linhas + membro -1). sk_hora = HHMM (ex.: 1430).
-- Hora local (America/Recife): os fatos convertem ocorrido_em antes de buscar a chave.
-- Limites dos períodos e janelas de pico: definição de negócio a validar pelo autor (vars em dbt_project.yml).
with minutos as (

    select
        cast(m as integer) as minuto_do_dia,
        cast(m // 60 as integer) as hora,
        cast(m % 60 as integer) as minuto,
        printf('%02d:%02d', cast(m // 60 as integer), cast(m % 60 as integer)) as hhmm
    from range(0, 1440) as t(m)

),

membros as (

    select
        cast(hora * 100 + minuto as integer) as sk_hora,
        hora,
        minuto,
        case
            when hhmm >= '{{ var("periodo_noite_inicio") }}' then 'noite'
            when hhmm >= '{{ var("periodo_tarde_inicio") }}' then 'tarde'
            when hhmm >= '{{ var("periodo_almoco_inicio") }}' then 'almoço'
            when hhmm >= '{{ var("periodo_cafe_da_manha_inicio") }}' then 'café da manhã'
            else 'madrugada'
        end as periodo_dia,
        hhmm between '{{ var("pico_almoco_inicio") }}' and '{{ var("pico_almoco_fim") }}'
            or hhmm between '{{ var("pico_jantar_inicio") }}' and '{{ var("pico_jantar_fim") }}' as eh_pico
    from minutos

)

select sk_hora, hora, minuto, cast(periodo_dia as varchar) as periodo_dia, eh_pico from membros
union all
select -1, cast(null as integer), cast(null as integer), 'não identificado', false
