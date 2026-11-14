-- Silver: eventos de domínio tipados e deduplicados por id_evento.
-- Entrega "ao menos uma vez" do bronze (releituras após falha) vira "exatamente uma vez" aqui:
-- mantém a primeira captura de cada evento (menor id_sequencial).
with raw as (

    select * from {{ source('bronze', 'outbox_eventos') }}

),

typed as (

    select
        cast(id_evento as uuid)             as id_evento,
        tipo_evento,
        cast(versao_schema as integer)      as versao_schema,
        tipo_agregado,
        id_agregado,
        cast(payload as json)               as payload,
        cast(ocorrido_em as timestamptz)    as ocorrido_em,
        cast(registrado_em as timestamptz)  as registrado_em,
        cast(id_sequencial as bigint)       as id_sequencial,
        cast(dt as date)                    as data_particao
    from raw

)

select *
from typed
qualify row_number() over (partition by id_evento order by id_sequencial) = 1
