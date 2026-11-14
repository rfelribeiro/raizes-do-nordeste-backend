import json
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from ingestao import extrair_outbox as ex
from ingestao import gerar_feriados as gh


def _row(seq: int, recorded_at: datetime) -> dict[str, Any]:
    return {
        "id_evento": f"00000000-0000-4000-8000-{seq:012d}",
        "tipo_evento": "evento_ficticio",
        "versao_schema": 1,
        "tipo_agregado": "teste",
        "id_agregado": str(seq),
        "payload": {"value": seq},
        "ocorrido_em": recorded_at,
        "registrado_em": recorded_at,
        "id_sequencial": seq,
    }


def test_partition_uses_utc_date() -> None:
    recife = timezone(timedelta(hours=-3))
    # 23:30 em Recife do dia 1 = 02:30 UTC do dia 2
    assert ex.partition_date(datetime(2026, 11, 1, 23, 30, tzinfo=recife)) == date(2026, 11, 2)


def test_partition_requires_timezone() -> None:
    with pytest.raises(ValueError):
        ex.partition_date(datetime(2026, 11, 1, 10, 0))


def test_group_by_partition() -> None:
    rows = [
        _row(1, datetime(2026, 11, 1, 23, 59, tzinfo=UTC)),
        _row(2, datetime(2026, 11, 2, 0, 1, tzinfo=UTC)),
        _row(3, datetime(2026, 11, 2, 8, 0, tzinfo=UTC)),
    ]
    groups = ex.group_by_partition(rows)
    assert list(groups) == [date(2026, 11, 1), date(2026, 11, 2)]
    assert [x["id_sequencial"] for x in groups[date(2026, 11, 2)]] == [2, 3]


def test_watermark_never_regresses() -> None:
    now = datetime(2026, 11, 2, tzinfo=UTC)
    assert ex.next_watermark(10, [_row(11, now), _row(15, now)]) == 15
    assert ex.next_watermark(10, []) == 10
    assert ex.next_watermark(10, [_row(3, now)]) == 10


def test_missing_state_starts_at_zero_and_writes_atomically(tmp_path: Path) -> None:
    file = ex.state_path(tmp_path)
    assert file == tmp_path / "_estado" / "outbox_eventos.json"
    assert ex.read_watermark(file) == 0
    ex.write_watermark(file, 42, "run-1")
    assert ex.read_watermark(file) == 42
    assert json.loads(file.read_text())["ultima_execucao_id"] == "run-1"
    assert not list(file.parent.glob("*.tmp"))


def test_lake_paths(tmp_path: Path) -> None:
    path = ex.partition_path(tmp_path, date(2026, 11, 2), "abc")
    assert path == tmp_path / "bronze" / "outbox_eventos" / "dt=2026-11-02" / "abc.parquet"


def test_row_to_bronze_converts_to_utc_and_serializes_payload() -> None:
    recife = timezone(timedelta(hours=-3))
    row = _row(7, datetime(2026, 11, 2, 9, 0, tzinfo=recife))
    bronze = ex.row_to_bronze(row)
    assert len(bronze) == len(ex.BRONZE_COLUMNS)
    assert bronze[6] == "2026-11-02T12:00:00+00:00"
    assert json.loads(bronze[5]) == {"value": 7}


def test_run_id_is_unique_and_sortable() -> None:
    a = ex.new_run_id(datetime(2026, 1, 1, tzinfo=UTC))
    b = ex.new_run_id(datetime(2026, 1, 2, tzinfo=UTC))
    assert a < b
    assert ex.new_run_id() != ex.new_run_id()


def test_esquema_vazio_is_idempotent(tmp_path: Path) -> None:
    duckdb = pytest.importorskip("duckdb")
    target = ex.ensure_empty_schema(tmp_path)
    assert target.name == "_esquema_vazio.parquet"
    before = target.stat().st_mtime_ns
    ex.ensure_empty_schema(tmp_path)
    assert target.stat().st_mtime_ns == before
    query = f"SELECT * FROM read_parquet('{target.as_posix()}', hive_partitioning = false)"
    columns = duckdb.sql(query).columns
    assert tuple(columns) == ex.COLUMN_NAMES


def test_easter_and_movable_holidays() -> None:
    assert gh.easter(2024) == date(2024, 3, 31)
    assert gh.easter(2025) == date(2025, 4, 20)
    assert gh.easter(2026) == date(2026, 4, 5)
    by_name = {name: day for day, name in gh.holidays_of_year(2026)}
    assert by_name["Sexta-feira Santa"] == date(2026, 4, 3)
    assert by_name["Corpus Christi"] == date(2026, 6, 4)


def test_holidays_cover_2024_to_2030_without_duplicate_dates() -> None:
    everything = gh.generate()
    dates = [day for day, _ in everything]
    assert len(dates) == len(set(dates))
    assert min(dates).year == 2024
    assert max(dates).year == 2030
