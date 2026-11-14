-- Silver: eventos de domínio tipados e deduplicados por event_id.
-- Entrega "ao menos uma vez" do bronze (releituras após falha) vira "exatamente uma vez" aqui:
-- mantém a primeira captura de cada evento (menor sequence_id).
with raw as (

    select * from {{ source('bronze', 'outbox_events') }}

),

typed as (

    select
        cast(event_id as uuid)                  as event_id,
        event_type,
        cast(schema_version as integer)         as schema_version,
        aggregate_type,
        aggregate_id,
        cast(payload as json)                   as payload,
        cast(occurred_at as timestamptz)        as occurred_at,
        cast(recorded_at as timestamptz)        as recorded_at,
        cast(sequence_id as bigint)             as sequence_id,
        cast(dt as date)                        as partition_date
    from raw

)

select *
from typed
qualify row_number() over (partition by event_id order by sequence_id) = 1
