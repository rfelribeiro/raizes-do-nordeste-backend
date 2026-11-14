"""Extração incremental da outbox (`outbox_events`) para a camada bronze do lake.

Fluxo de uma execução:
  1. lê a marca d'água (último `sequence_id` já extraído) de `_state/outbox_events.json`;
  2. consulta `outbox_events` com `sequence_id > marca d'água`, em ordem;
  3. agrupa as linhas por data de captura (UTC) e grava um Parquet por partição:
     `bronze/outbox_events/dt=AAAA-MM-DD/<run_id>.parquet` (imutável, append-only);
  4. SOMENTE depois de gravar todos os arquivos, atualiza a marca d'água.

Idempotência: sem eventos novos nada é gravado; se a execução falhar antes do passo 4, a marca
d'água não avança e a próxima execução relê as mesmas linhas (arquivos órfãos da execução que
falhou ficam com outro `run_id`; a silver deduplica por `event_id`, então não há dupla
contagem — ao menos uma vez + deduplicação = efeito exatamente uma vez).

Atraso de segurança: transações concorrentes podem confirmar `sequence_id` fora de ordem.
Para não pular um evento que confirma "atrasado", só são lidas linhas com `recorded_at`
anterior a (agora - atraso). Transações mais longas que o atraso de segurança ainda são um risco
residual, documentado em analytics/README.md.

Credenciais: lidas das mesmas variáveis de ambiente da API (POSTGRES_*); nunca logadas.
"""

import argparse
import json
import logging
import os
import sys
import uuid
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ingestion.extract_outbox")

TABLE_NAME = "outbox_events"
EMPTY_SCHEMA_DATE = "1970-01-01"
EMPTY_SCHEMA_FILE = "_empty_schema.parquet"
DEFAULT_LAG_SECONDS = 5

# Esquema do bronze: espelha a tabela de origem; datas em texto ISO-8601 UTC (bruto, sem tipagem
# interpretativa). A tipagem acontece na silver (stg_outbox_events).
BRONZE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("event_id", "VARCHAR"),
    ("event_type", "VARCHAR"),
    ("schema_version", "INTEGER"),
    ("aggregate_type", "VARCHAR"),
    ("aggregate_id", "VARCHAR"),
    ("payload", "VARCHAR"),
    ("occurred_at", "VARCHAR"),
    ("recorded_at", "VARCHAR"),
    ("sequence_id", "BIGINT"),
)
COLUMN_NAMES = tuple(name for name, _ in BRONZE_COLUMNS)


# --------------------------------------------------------------------------------------------
# Funções puras (sem I/O)
# --------------------------------------------------------------------------------------------


def partition_date(recorded_at: datetime) -> date:
    """Data (UTC) usada na partição `dt=` a partir do instante de captura do evento."""
    if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
        raise ValueError("recorded_at deve ter fuso horário")
    return recorded_at.astimezone(UTC).date()


def group_by_partition(
    rows: Iterable[Mapping[str, Any]],
) -> dict[date, list[Mapping[str, Any]]]:
    """Agrupa as linhas pela data de captura (UTC), preservando a ordem de entrada."""
    groups: dict[date, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[partition_date(row["recorded_at"])].append(row)
    return dict(sorted(groups.items()))


def next_watermark(current: int, rows: Sequence[Mapping[str, Any]]) -> int:
    """Maior `sequence_id` visto; a marca d'água nunca regride."""
    return max([current, *(int(row["sequence_id"]) for row in rows)])


def partition_path(lake_root: Path, day: date, run_id: str) -> Path:
    return lake_root / "bronze" / TABLE_NAME / f"dt={day.isoformat()}" / f"{run_id}.parquet"


def empty_schema_path(lake_root: Path) -> Path:
    return lake_root / "bronze" / TABLE_NAME / f"dt={EMPTY_SCHEMA_DATE}" / EMPTY_SCHEMA_FILE


def state_path(lake_root: Path) -> Path:
    return lake_root / "_state" / f"{TABLE_NAME}.json"


def row_to_bronze(row: Mapping[str, Any]) -> tuple[Any, ...]:
    """Converte uma linha do Postgres para a tupla do bronze (datas em ISO UTC, payload JSON)."""
    payload = row["payload"]
    return (
        str(row["event_id"]),
        row["event_type"],
        int(row["schema_version"]),
        row["aggregate_type"],
        row["aggregate_id"],
        payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False),
        row["occurred_at"].astimezone(UTC).isoformat(),
        row["recorded_at"].astimezone(UTC).isoformat(),
        int(row["sequence_id"]),
    )


def new_run_id(now: datetime | None = None) -> str:
    """Identificador ordenável no tempo e único: AAAAMMDDTHHMMSSZ-<8 hex>."""
    instant = (now or datetime.now(UTC)).astimezone(UTC)
    return f"{instant:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"


# --------------------------------------------------------------------------------------------
# Estado (marca d'água)
# --------------------------------------------------------------------------------------------


def read_watermark(file: Path) -> int:
    if not file.exists():
        return 0
    data = json.loads(file.read_text(encoding="utf-8"))
    return int(data["last_sequence_id"])


def write_watermark(file: Path, value: int, run_id: str) -> None:
    """Grava de forma atômica (arquivo temporário + rename)."""
    file.parent.mkdir(parents=True, exist_ok=True)
    temp = file.with_suffix(".json.tmp")
    temp.write_text(
        json.dumps(
            {
                "last_sequence_id": value,
                "last_run_id": run_id,
                "updated_at": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    os.replace(temp, file)


# --------------------------------------------------------------------------------------------
# I/O: Parquet (DuckDB) e Postgres (psycopg)
# --------------------------------------------------------------------------------------------


def _write_parquet(target: Path, rows: Sequence[tuple[Any, ...]]) -> None:
    import duckdb

    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".parquet.tmp")
    definition = ", ".join(f"{name} {type_}" for name, type_ in BRONZE_COLUMNS)
    connection = duckdb.connect(":memory:")
    try:
        connection.execute(f"CREATE TABLE batch ({definition})")
        if rows:
            placeholders = ", ".join("?" for _ in BRONZE_COLUMNS)
            connection.executemany(f"INSERT INTO batch VALUES ({placeholders})", list(rows))
        connection.execute(f"COPY batch TO '{temp.as_posix()}' (FORMAT parquet)")
    finally:
        connection.close()
    os.replace(temp, target)


def ensure_empty_schema(lake_root: Path) -> Path:
    """Cria (se ausente) um Parquet com 0 linhas e o esquema do bronze.

    Sem ele, o glob do bronze não encontraria arquivo algum quando ainda não há eventos e a
    silver falharia. Com ele, `read_parquet` devolve 0 linhas com as colunas corretas.
    """
    target = empty_schema_path(lake_root)
    if not target.exists():
        _write_parquet(target, [])
    return target


def _connect_postgres() -> Any:
    import psycopg

    return psycopg.connect(
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        connect_timeout=10,
    )


def fetch_new_events(watermark: int, lag_seconds: int) -> list[dict[str, Any]]:
    query = f"""
        SELECT {", ".join(COLUMN_NAMES)}
        FROM outbox_events
        WHERE sequence_id > %s
          AND recorded_at <= now() - make_interval(secs => %s)
        ORDER BY sequence_id
    """
    with _connect_postgres() as connection, connection.cursor() as cursor:
        cursor.execute(query, (watermark, lag_seconds))
        return [dict(zip(COLUMN_NAMES, row, strict=True)) for row in cursor.fetchall()]


@dataclass(frozen=True)
class ExtractionResult:
    run_id: str
    rows: int
    files: tuple[Path, ...]
    watermark: int


def extract(lake_root: Path, lag_seconds: int = DEFAULT_LAG_SECONDS) -> ExtractionResult:
    ensure_empty_schema(lake_root)
    state_file = state_path(lake_root)
    current_watermark = read_watermark(state_file)
    run_id = new_run_id()

    rows = fetch_new_events(current_watermark, lag_seconds)
    if not rows:
        logger.info("Nenhum evento novo (marca d'água em %s).", current_watermark)
        return ExtractionResult(run_id, 0, (), current_watermark)

    files: list[Path] = []
    for day, group in group_by_partition(rows).items():
        target = partition_path(lake_root, day, run_id)
        _write_parquet(target, [row_to_bronze(row) for row in group])
        files.append(target)

    # Passo final: só avança a marca d'água depois que TODOS os arquivos foram gravados.
    new_watermark = next_watermark(current_watermark, rows)
    write_watermark(state_file, new_watermark, run_id)
    logger.info(
        "Extraídos %s evento(s) em %s arquivo(s); marca d'água %s -> %s.",
        len(rows),
        len(files),
        current_watermark,
        new_watermark,
    )
    return ExtractionResult(run_id, len(rows), tuple(files), new_watermark)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument(
        "--lake",
        default=os.environ.get("DW_LAKE_PATH", "data/lake"),
        help="raiz do lake (padrão: $DW_LAKE_PATH ou data/lake)",
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="apenas garante o Parquet de esquema vazio do bronze (não acessa o banco)",
    )
    parser.add_argument(
        "--lag-seconds",
        type=int,
        default=int(os.environ.get("DW_EXTRACTION_LAG_SECONDS", str(DEFAULT_LAG_SECONDS))),
        help="ignora eventos registrados há menos de N segundos (padrão: %(default)s)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    root = Path(args.lake)
    if args.schema_only:
        ensure_empty_schema(root)
        logger.info("Esquema vazio do bronze garantido em %s.", root)
        return 0
    try:
        result = extract(root, args.lag_seconds)
    except Exception as error:
        # Não usa exc_info: o traceback de conexão poderia expor detalhes do ambiente.
        logger.error("Falha na extração: %s", type(error).__name__)
        return 1
    logger.info("Concluído: %s linha(s), marca d'água %s.", result.rows, result.watermark)
    return 0


if __name__ == "__main__":
    sys.exit(main())
