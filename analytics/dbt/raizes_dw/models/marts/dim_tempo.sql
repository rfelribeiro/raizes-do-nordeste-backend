-- Gold: dimensão de tempo (calendário diário). Única dimensão fornecida pela IA;
-- as dimensões e fatos de negócio são de autoria do arquiteto (ver docs/dados/).
--
-- Fuso: a data aqui é a data CIVIL em America/Recife. Os eventos são armazenados em UTC e, ao
-- carregar um fato, convertem-se para essa data: cast(ocorrido_em at time zone 'America/Recife' as date).
--
-- eh_periodo_junino: definição de negócio a validar pelo autor (vars periodo_junino_inicio/fim).
-- Os valores textuais (nomes de mês, de dia e de feriado) permanecem em português.
with calendario as (

    select cast(dia_ts as date) as data
    from generate_series(
        cast('{{ var("dim_tempo_data_inicio") }}' as date),
        cast('{{ var("dim_tempo_data_fim") }}' as date),
        interval 1 day
    ) as t(dia_ts)

),

feriados as (

    select
        data_feriado,
        -- 1 nome por data (ex.: se dois feriados coincidirem, concatena)
        string_agg(nome_feriado, ' / ' order by nome_feriado) as nome_feriado
    from {{ ref('feriados_nacionais') }}
    group by data_feriado

)

select
    cast(strftime(c.data, '%Y%m%d') as integer)                             as sk_data,
    c.data                                                                  as data,
    cast(year(c.data) as integer)                                           as ano,
    cast(quarter(c.data) as integer)                                        as trimestre,
    cast(month(c.data) as integer)                                          as mes,
    (array['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
           'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'])[month(c.data)] as nome_mes,
    cast(day(c.data) as integer)                                            as dia_mes,
    cast(isodow(c.data) as integer)                                         as dia_semana,
    (array['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira',
           'sexta-feira', 'sábado', 'domingo'])[isodow(c.data)]            as nome_dia_semana,
    isodow(c.data) in (6, 7)                                                as eh_fim_de_semana,
    f.data_feriado is not null                                              as eh_feriado_nacional,
    f.nome_feriado                                                          as nome_feriado,
    strftime(c.data, '%m-%d') between '{{ var("periodo_junino_inicio") }}'
        and '{{ var("periodo_junino_fim") }}'                               as eh_periodo_junino
from calendario as c
left join feriados as f on f.data_feriado = c.data
