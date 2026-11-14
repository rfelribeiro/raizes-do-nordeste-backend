-- Gold: dimensão de data genérica (calendário). Única dimensão fornecida pela IA;
-- as dimensões e fatos de negócio são de autoria do arquiteto (ver docs/dados/).
--
-- Fuso: a data aqui é a data CIVIL em America/Recife. Os eventos são armazenados em UTC e, ao
-- carregar uma fato, convertem-se para essa data: cast(occurred_at at time zone 'America/Recife' as date).
--
-- is_festa_junina_season: definição de negócio a validar pelo autor (vars festa_junina_season_start/end).
-- Os valores textuais (nomes de mês, de dia e de feriado) permanecem em português.
with calendar as (

    select cast(day_ts as date) as full_date
    from generate_series(
        cast('{{ var("dim_date_start_date") }}' as date),
        cast('{{ var("dim_date_end_date") }}' as date),
        interval 1 day
    ) as t(day_ts)

),

holidays as (

    select
        holiday_date,
        -- 1 nome por data (ex.: se dois feriados coincidirem, concatena)
        string_agg(holiday_name, ' / ' order by holiday_name) as holiday_name
    from {{ ref('national_holidays') }}
    group by holiday_date

)

select
    cast(strftime(c.full_date, '%Y%m%d') as integer)                        as date_key,
    c.full_date                                                             as full_date,
    cast(year(c.full_date) as integer)                                      as year,
    cast(quarter(c.full_date) as integer)                                   as quarter,
    cast(month(c.full_date) as integer)                                     as month,
    (array['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
           'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'])[month(c.full_date)] as month_name,
    cast(day(c.full_date) as integer)                                       as day_of_month,
    cast(isodow(c.full_date) as integer)                                    as day_of_week,
    (array['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira',
           'sexta-feira', 'sábado', 'domingo'])[isodow(c.full_date)]       as day_of_week_name,
    isodow(c.full_date) in (6, 7)                                           as is_weekend,
    h.holiday_date is not null                                              as is_national_holiday,
    h.holiday_name                                                          as holiday_name,
    strftime(c.full_date, '%m-%d') between '{{ var("festa_junina_season_start") }}'
        and '{{ var("festa_junina_season_end") }}'                          as is_festa_junina_season
from calendar as c
left join holidays as h on h.holiday_date = c.full_date
