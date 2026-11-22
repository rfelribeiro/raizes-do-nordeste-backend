"""Silver intermediária: mapa id do cliente -> chave substituta e pseudônimo (HMAC-SHA256).

O DuckDB não tem HMAC nativo; por isso este modelo é Python (módulos `hmac` e `hashlib`).
A chave vem de ANALYTICS_PSEUDONYM_KEY; nunca é logada nem gravada. Este modelo guarda o id em
claro (necessário para ligar o fato ao cliente) e fica na silver; a gold (`dim_cliente`) só expõe
o pseudônimo. Contratos do dbt não se aplicam a modelos Python, por isso não há `contract` aqui.
"""

import hashlib
import hmac
import os


def model(dbt, session):
    dbt.config(materialized="table")

    chave = os.environ.get("ANALYTICS_PSEUDONYM_KEY", "")
    if not chave:
        raise RuntimeError(
            "A variável de ambiente ANALYTICS_PSEUDONYM_KEY não está definida. "
            "Rode `make setup` (gera o .env) ou, na CI, defina um valor fictício."
        )
    chave_bytes = chave.encode("utf-8")

    def hmac_sha256_hex(valor):
        if valor is None:
            return None
        return hmac.new(chave_bytes, valor.encode("utf-8"), hashlib.sha256).hexdigest()

    # Sem UDF (exigiria numpy, fora das dependências): lê os ids, calcula o HMAC em Python e grava.
    eventos = dbt.ref("stg_outbox_eventos")
    ids = eventos.query(
        "eventos",
        """
        select id_cliente
        from (
            select payload ->> 'cliente_id' as id_cliente, min(id_sequencial) as primeira_captura
            from eventos
            where tipo_evento = 'pedido_criado' and (payload ->> 'cliente_id') is not null
            group by 1
        )
        order by primeira_captura
        """,
    ).fetchall()
    linhas = [(n, i[0], hmac_sha256_hex(i[0])) for n, i in enumerate(ids, start=1)]

    session.execute(
        "create or replace temp table _mapa_cliente "
        "(sk_cliente integer, id_cliente varchar, id_cliente_pseudonimo varchar)"
    )
    if linhas:
        session.executemany("insert into _mapa_cliente values (?, ?, ?)", linhas)
    return session.sql("select * from _mapa_cliente")
