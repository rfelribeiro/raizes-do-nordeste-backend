"""Extração incremental da outbox (`outbox_eventos`) para a camada bronze do lake.

Fluxo de uma execução:
  1. lê a marca d'água (último `id_sequencial` já extraído) de `_estado/outbox_eventos.json`;
  2. consulta `outbox_eventos` com `id_sequencial > marca d'água`, em ordem;
  3. agrupa as linhas por data de captura (UTC) e grava um Parquet por partição:
     `bronze/outbox_eventos/dt=AAAA-MM-DD/<id_execucao>.parquet` (imutável, append-only);
  4. SOMENTE depois de gravar todos os arquivos, atualiza a marca d'água.

Idempotência: sem eventos novos nada é gravado; se a execução falhar antes do passo 4, a marca
d'água não avança e a próxima execução relê as mesmas linhas (arquivos órfãos da execução que
falhou ficam com outro `id_execucao`; a silver deduplica por `id_evento`, então não há dupla
contagem — ao menos uma vez + deduplicação = efeito exatamente uma vez).

Defasagem de segurança: transações concorrentes podem confirmar `id_sequencial` fora de ordem.
Para não pular um evento que confirma "atrasado", só são lidas linhas com `registrado_em`
anterior a (agora - defasagem). Transações mais longas que a defasagem ainda são um risco
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

logger = logging.getLogger("ingestao.extrair_outbox")

NOME_TABELA = "outbox_eventos"
DATA_ESQUEMA_VAZIO = "1970-01-01"
ARQUIVO_ESQUEMA_VAZIO = "_esquema_vazio.parquet"
DEFASAGEM_PADRAO_SEGUNDOS = 5

# Esquema do bronze: espelha a tabela de origem; datas em texto ISO-8601 UTC (bruto, sem tipagem
# interpretativa). A tipagem acontece na silver (stg_outbox_eventos).
COLUNAS_BRONZE: tuple[tuple[str, str], ...] = (
    ("id_evento", "VARCHAR"),
    ("tipo_evento", "VARCHAR"),
    ("versao_schema", "INTEGER"),
    ("tipo_agregado", "VARCHAR"),
    ("id_agregado", "VARCHAR"),
    ("payload", "VARCHAR"),
    ("ocorrido_em", "VARCHAR"),
    ("registrado_em", "VARCHAR"),
    ("id_sequencial", "BIGINT"),
)
NOMES_COLUNAS = tuple(nome for nome, _ in COLUNAS_BRONZE)


# --------------------------------------------------------------------------------------------
# Funções puras (sem I/O)
# --------------------------------------------------------------------------------------------


def data_de_particao(registrado_em: datetime) -> date:
    """Data (UTC) usada na partição `dt=` a partir do instante de captura do evento."""
    if registrado_em.tzinfo is None or registrado_em.utcoffset() is None:
        raise ValueError("registrado_em deve ter fuso horário")
    return registrado_em.astimezone(UTC).date()


def agrupar_por_particao(
    linhas: Iterable[Mapping[str, Any]],
) -> dict[date, list[Mapping[str, Any]]]:
    """Agrupa as linhas pela data de captura (UTC), preservando a ordem de entrada."""
    grupos: dict[date, list[Mapping[str, Any]]] = defaultdict(list)
    for linha in linhas:
        grupos[data_de_particao(linha["registrado_em"])].append(linha)
    return dict(sorted(grupos.items()))


def proxima_marca_dagua(atual: int, linhas: Sequence[Mapping[str, Any]]) -> int:
    """Maior `id_sequencial` visto; a marca d'água nunca regride."""
    return max([atual, *(int(linha["id_sequencial"]) for linha in linhas)])


def caminho_particao(raiz_lake: Path, dia: date, id_execucao: str) -> Path:
    return raiz_lake / "bronze" / NOME_TABELA / f"dt={dia.isoformat()}" / f"{id_execucao}.parquet"


def caminho_esquema_vazio(raiz_lake: Path) -> Path:
    return raiz_lake / "bronze" / NOME_TABELA / f"dt={DATA_ESQUEMA_VAZIO}" / ARQUIVO_ESQUEMA_VAZIO


def caminho_estado(raiz_lake: Path) -> Path:
    return raiz_lake / "_estado" / f"{NOME_TABELA}.json"


def linha_para_bronze(linha: Mapping[str, Any]) -> tuple[Any, ...]:
    """Converte uma linha do Postgres para a tupla do bronze (datas em ISO UTC, payload JSON)."""
    payload = linha["payload"]
    return (
        str(linha["id_evento"]),
        linha["tipo_evento"],
        int(linha["versao_schema"]),
        linha["tipo_agregado"],
        linha["id_agregado"],
        payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False),
        linha["ocorrido_em"].astimezone(UTC).isoformat(),
        linha["registrado_em"].astimezone(UTC).isoformat(),
        int(linha["id_sequencial"]),
    )


def novo_id_execucao(agora: datetime | None = None) -> str:
    """Identificador ordenável no tempo e único: AAAAMMDDTHHMMSSZ-<8 hex>."""
    instante = (agora or datetime.now(UTC)).astimezone(UTC)
    return f"{instante:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"


# --------------------------------------------------------------------------------------------
# Estado (marca d'água)
# --------------------------------------------------------------------------------------------


def ler_marca_dagua(arquivo: Path) -> int:
    if not arquivo.exists():
        return 0
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    return int(dados["ultimo_id_sequencial"])


def gravar_marca_dagua(arquivo: Path, valor: int, id_execucao: str) -> None:
    """Grava de forma atômica (arquivo temporário + rename)."""
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    temporario = arquivo.with_suffix(".json.tmp")
    temporario.write_text(
        json.dumps(
            {
                "ultimo_id_sequencial": valor,
                "ultima_execucao": id_execucao,
                "atualizado_em": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    os.replace(temporario, arquivo)


# --------------------------------------------------------------------------------------------
# I/O: Parquet (DuckDB) e Postgres (psycopg)
# --------------------------------------------------------------------------------------------


def _escrever_parquet(destino: Path, linhas: Sequence[tuple[Any, ...]]) -> None:
    import duckdb

    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".parquet.tmp")
    definicao = ", ".join(f"{nome} {tipo}" for nome, tipo in COLUNAS_BRONZE)
    conexao = duckdb.connect(":memory:")
    try:
        conexao.execute(f"CREATE TABLE lote ({definicao})")
        if linhas:
            marcadores = ", ".join("?" for _ in COLUNAS_BRONZE)
            conexao.executemany(f"INSERT INTO lote VALUES ({marcadores})", list(linhas))
        conexao.execute(f"COPY lote TO '{temporario.as_posix()}' (FORMAT parquet)")
    finally:
        conexao.close()
    os.replace(temporario, destino)


def garantir_esquema_vazio(raiz_lake: Path) -> Path:
    """Cria (se ausente) um Parquet com 0 linhas e o esquema do bronze.

    Sem ele, o glob do bronze não encontraria arquivo algum quando ainda não há eventos e a
    silver falharia. Com ele, `read_parquet` devolve 0 linhas com as colunas corretas.
    """
    destino = caminho_esquema_vazio(raiz_lake)
    if not destino.exists():
        _escrever_parquet(destino, [])
    return destino


def _conectar_postgres() -> Any:
    import psycopg

    return psycopg.connect(
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        connect_timeout=10,
    )


def buscar_novos_eventos(marca_dagua: int, defasagem_segundos: int) -> list[dict[str, Any]]:
    consulta = f"""
        SELECT {", ".join(NOMES_COLUNAS)}
        FROM outbox_eventos
        WHERE id_sequencial > %s
          AND registrado_em <= now() - make_interval(secs => %s)
        ORDER BY id_sequencial
    """
    with _conectar_postgres() as conexao, conexao.cursor() as cursor:
        cursor.execute(consulta, (marca_dagua, defasagem_segundos))
        return [dict(zip(NOMES_COLUNAS, linha, strict=True)) for linha in cursor.fetchall()]


@dataclass(frozen=True)
class ResultadoExtracao:
    id_execucao: str
    linhas: int
    arquivos: tuple[Path, ...]
    marca_dagua: int


def extrair(
    raiz_lake: Path, defasagem_segundos: int = DEFASAGEM_PADRAO_SEGUNDOS
) -> ResultadoExtracao:
    garantir_esquema_vazio(raiz_lake)
    arquivo_estado = caminho_estado(raiz_lake)
    marca_atual = ler_marca_dagua(arquivo_estado)
    id_execucao = novo_id_execucao()

    linhas = buscar_novos_eventos(marca_atual, defasagem_segundos)
    if not linhas:
        logger.info("Nenhum evento novo (marca d'água em %s).", marca_atual)
        return ResultadoExtracao(id_execucao, 0, (), marca_atual)

    arquivos: list[Path] = []
    for dia, grupo in agrupar_por_particao(linhas).items():
        destino = caminho_particao(raiz_lake, dia, id_execucao)
        _escrever_parquet(destino, [linha_para_bronze(linha) for linha in grupo])
        arquivos.append(destino)

    # Passo final: só avança a marca d'água depois que TODOS os arquivos foram gravados.
    nova_marca = proxima_marca_dagua(marca_atual, linhas)
    gravar_marca_dagua(arquivo_estado, nova_marca, id_execucao)
    logger.info(
        "Extraídos %s evento(s) em %s arquivo(s); marca d'água %s -> %s.",
        len(linhas),
        len(arquivos),
        marca_atual,
        nova_marca,
    )
    return ResultadoExtracao(id_execucao, len(linhas), tuple(arquivos), nova_marca)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument(
        "--lake",
        default=os.environ.get("DW_LAKE_PATH", "data/lake"),
        help="raiz do lake (padrão: $DW_LAKE_PATH ou data/lake)",
    )
    parser.add_argument(
        "--somente-esquema",
        action="store_true",
        help="apenas garante o Parquet de esquema vazio do bronze (não acessa o banco)",
    )
    parser.add_argument(
        "--defasagem-segundos",
        type=int,
        default=int(
            os.environ.get("DW_EXTRACAO_DEFASAGEM_SEGUNDOS", str(DEFASAGEM_PADRAO_SEGUNDOS))
        ),
        help="ignora eventos registrados há menos de N segundos (padrão: %(default)s)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    raiz = Path(args.lake)
    if args.somente_esquema:
        garantir_esquema_vazio(raiz)
        logger.info("Esquema vazio do bronze garantido em %s.", raiz)
        return 0
    try:
        resultado = extrair(raiz, args.defasagem_segundos)
    except Exception as erro:
        # Não usa exc_info: o traceback de conexão poderia expor detalhes do ambiente.
        logger.error("Falha na extração: %s", type(erro).__name__)
        return 1
    logger.info("Concluído: %s linha(s), marca d'água %s.", resultado.linhas, resultado.marca_dagua)
    return 0


if __name__ == "__main__":
    sys.exit(main())
