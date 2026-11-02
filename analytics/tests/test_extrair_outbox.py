import json
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from ingestao import extrair_outbox as ex
from ingestao import gerar_feriados as gf


def _linha(seq: int, registrado_em: datetime) -> dict[str, Any]:
    return {
        "id_evento": f"00000000-0000-4000-8000-{seq:012d}",
        "tipo_evento": "evento_ficticio",
        "versao_schema": 1,
        "tipo_agregado": "teste",
        "id_agregado": str(seq),
        "payload": {"valor": seq},
        "ocorrido_em": registrado_em,
        "registrado_em": registrado_em,
        "id_sequencial": seq,
    }


def test_particao_usa_data_utc() -> None:
    recife = timezone(timedelta(hours=-3))
    # 23:30 em Recife do dia 1 = 02:30 UTC do dia 2
    assert ex.data_de_particao(datetime(2026, 11, 1, 23, 30, tzinfo=recife)) == date(2026, 11, 2)


def test_particao_exige_fuso() -> None:
    with pytest.raises(ValueError):
        ex.data_de_particao(datetime(2026, 11, 1, 10, 0))


def test_agrupar_por_particao() -> None:
    linhas = [
        _linha(1, datetime(2026, 11, 1, 23, 59, tzinfo=UTC)),
        _linha(2, datetime(2026, 11, 2, 0, 1, tzinfo=UTC)),
        _linha(3, datetime(2026, 11, 2, 8, 0, tzinfo=UTC)),
    ]
    grupos = ex.agrupar_por_particao(linhas)
    assert list(grupos) == [date(2026, 11, 1), date(2026, 11, 2)]
    assert [x["id_sequencial"] for x in grupos[date(2026, 11, 2)]] == [2, 3]


def test_marca_dagua_nunca_regride() -> None:
    agora = datetime(2026, 11, 2, tzinfo=UTC)
    assert ex.proxima_marca_dagua(10, [_linha(11, agora), _linha(15, agora)]) == 15
    assert ex.proxima_marca_dagua(10, []) == 10
    assert ex.proxima_marca_dagua(10, [_linha(3, agora)]) == 10


def test_estado_ausente_comeca_em_zero_e_grava_atomicamente(tmp_path: Path) -> None:
    arquivo = ex.caminho_estado(tmp_path)
    assert ex.ler_marca_dagua(arquivo) == 0
    ex.gravar_marca_dagua(arquivo, 42, "exec-1")
    assert ex.ler_marca_dagua(arquivo) == 42
    assert json.loads(arquivo.read_text())["ultima_execucao"] == "exec-1"
    assert not list(arquivo.parent.glob("*.tmp"))


def test_caminhos_do_lake(tmp_path: Path) -> None:
    caminho = ex.caminho_particao(tmp_path, date(2026, 11, 2), "abc")
    assert caminho == tmp_path / "bronze" / "outbox_eventos" / "dt=2026-11-02" / "abc.parquet"


def test_linha_para_bronze_converte_para_utc_e_serializa_payload() -> None:
    recife = timezone(timedelta(hours=-3))
    linha = _linha(7, datetime(2026, 11, 2, 9, 0, tzinfo=recife))
    bronze = ex.linha_para_bronze(linha)
    assert len(bronze) == len(ex.COLUNAS_BRONZE)
    assert bronze[6] == "2026-11-02T12:00:00+00:00"
    assert json.loads(bronze[5]) == {"valor": 7}


def test_id_execucao_e_unico_e_ordenavel() -> None:
    a = ex.novo_id_execucao(datetime(2026, 1, 1, tzinfo=UTC))
    b = ex.novo_id_execucao(datetime(2026, 1, 2, tzinfo=UTC))
    assert a < b
    assert ex.novo_id_execucao() != ex.novo_id_execucao()


def test_esquema_vazio_idempotente(tmp_path: Path) -> None:
    duckdb = pytest.importorskip("duckdb")
    destino = ex.garantir_esquema_vazio(tmp_path)
    antes = destino.stat().st_mtime_ns
    ex.garantir_esquema_vazio(tmp_path)
    assert destino.stat().st_mtime_ns == antes
    consulta = f"SELECT * FROM read_parquet('{destino.as_posix()}', hive_partitioning = false)"
    colunas = duckdb.sql(consulta).columns
    assert tuple(colunas) == ex.NOMES_COLUNAS


def test_pascoa_e_feriados_moveis() -> None:
    assert gf.pascoa(2024) == date(2024, 3, 31)
    assert gf.pascoa(2025) == date(2025, 4, 20)
    assert gf.pascoa(2026) == date(2026, 4, 5)
    por_nome = {nome: dia for dia, nome in gf.feriados_do_ano(2026)}
    assert por_nome["Sexta-feira Santa"] == date(2026, 4, 3)
    assert por_nome["Corpus Christi"] == date(2026, 6, 4)


def test_feriados_cobrem_2024_a_2030_sem_duplicar_datas() -> None:
    todos = gf.gerar()
    datas = [dia for dia, _ in todos]
    assert len(datas) == len(set(datas))
    assert min(datas).year == 2024
    assert max(datas).year == 2030
