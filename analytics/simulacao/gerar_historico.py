"""Gerador de histórico SINTÉTICO de eventos de domínio (dados 100% fictícios).

Produz, num lake SEPARADO do real, Parquets no mesmo esquema do bronze da outbox:

    data/lake_simulado/bronze/outbox_eventos/dt=AAAA-MM-DD/<arquivo>.parquet

O lake real (`data/lake`) nunca é tocado: o gerador recusa um destino cujo nome não contenha
"simulado" (a menos que se passe `--forcar`). Nenhum dado pessoal é gerado: só UUIDs, valores,
canais, status e formas de pagamento (os payloads seguem `src/raizes/domain/orders/events.py`).

Para dar série temporal a um painel de demonstração, o gerador imita padrões plausíveis de uma rede
de lanchonetes regionais. Os parâmetros ficam no topo do arquivo (todos ajustáveis). A simulação é
DETERMINÍSTICA: a mesma semente produz exatamente os mesmos eventos (incluindo UUIDs).

Uso (dentro do contêiner do serviço `analytics`, via `make dw-simulado`):

    python -m simulacao.gerar_historico --semente 2026 --inicio 2026-01-01 --fim 2026-11-20
"""

import argparse
import logging
import math
import random
import shutil
import sys
import uuid
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from ingestao import extrair_outbox as bronze

logger = logging.getLogger("simulacao.gerar_historico")

# =============================================================================================
# PARÂMETROS DA SIMULAÇÃO (tudo fictício; ajuste aqui)
# =============================================================================================

SEMENTE_PADRAO = 2026
INICIO_PADRAO = date(2026, 1, 1)
FIM_PADRAO = date(2026, 11, 20)
PEDIDOS_ALVO_PADRAO = 32_000  # ordem de grandeza do volume total no período padrão

# Versão do esquema do payload (a mesma do evento real: `DomainEvent.schema_version`).
VERSAO_SCHEMA = 1

# America/Recife é UTC-3 o ano todo (sem horário de verão desde 2019): offset fixo, sem tzdata.
FUSO_RECIFE = timezone(timedelta(hours=-3), "America/Recife")

# Namespace constante para UUIDs determinísticos (unidades extras, clientes, pedidos, eventos).
NAMESPACE = uuid.UUID("5b0f5f0e-6a43-5c7e-9d1e-0a11f0e5a1b2")

# --- Unidades ------------------------------------------------------------------------------
# As duas primeiras reproduzem os UUIDs FIXOS de `scripts/seed.py` (101 e 102). O seed só tem
# duas unidades; para o painel ter comparação por unidade e região, acrescentam-se duas unidades
# FICTÍCIAS com UUIDs fixos derivados por uuid5(NAMESPACE, "unidade-<código>").
# (id, formato, participação no volume, mix de canais)
UNIDADES: tuple[dict[str, Any], ...] = (
    {  # seed: Raízes Boa Viagem (demo), Recife, COMPLETA: salão grande, mais balcão e totem
        "id": "00000000-0000-4000-8000-000000000101",
        "peso": 0.36,
        "canais": {"APP": 0.20, "WEB": 0.10, "PICKUP": 0.08, "TOTEM": 0.27, "BALCAO": 0.35},
    },
    {  # seed: Raízes Beira-Mar (demo), Fortaleza, REDUZIDA: formato reduzido, mais APP e PICKUP
        "id": "00000000-0000-4000-8000-000000000102",
        "peso": 0.22,
        "canais": {"APP": 0.42, "WEB": 0.14, "PICKUP": 0.26, "TOTEM": 0.06, "BALCAO": 0.12},
    },
    {  # fictícia: Salvador, COMPLETA
        "id": str(uuid.uuid5(NAMESPACE, "unidade-SSA-01")),
        "peso": 0.26,
        "canais": {"APP": 0.28, "WEB": 0.12, "PICKUP": 0.12, "TOTEM": 0.22, "BALCAO": 0.26},
    },
    {  # fictícia: Natal, REDUZIDA
        "id": str(uuid.uuid5(NAMESPACE, "unidade-NAT-01")),
        "peso": 0.16,
        "canais": {"APP": 0.36, "WEB": 0.10, "PICKUP": 0.22, "TOTEM": 0.10, "BALCAO": 0.22},
    },
)

# --- Ticket médio por canal (R$) e dispersão (sigma da lognormal) ------------------------------
TICKET_MEDIO = {"APP": 49.0, "WEB": 53.0, "PICKUP": 42.0, "TOTEM": 39.0, "BALCAO": 34.0}
TICKET_SIGMA = 0.38
TICKET_MINIMO = Decimal("9.00")
AUMENTO_TICKET_JUNINO = 1.08  # pratos e combos juninos elevam o ticket em jun/jul

# --- Cliente identificado ------------------------------------------------------------------
# Probabilidade de o pedido NÃO ter cliente (cliente_id nulo), por canal. Com o mix acima o
# resultado global fica em torno de 40% sem cliente. (RN-14: BALCAO/TOTEM são registrados por
# atendente/totem e raramente identificam o cliente; APP exige login.)
PROB_SEM_CLIENTE = {"APP": 0.03, "WEB": 0.20, "PICKUP": 0.30, "TOTEM": 0.62, "BALCAO": 0.72}
CLIENTES_RECORRENTES = 6_000  # pool de clientes fictícios (UUIDs); uso enviesado para poucos fiéis
EXPOENTE_FIDELIDADE = 2.2  # >1 concentra as compras nos primeiros clientes do pool

# --- Sazonalidade --------------------------------------------------------------------------
# Fator por dia da semana (1=segunda ... 7=domingo): sexta e sábado maiores.
FATOR_DIA_SEMANA = {1: 0.85, 2: 0.85, 3: 0.92, 4: 1.00, 5: 1.25, 6: 1.35, 7: 1.05}
# Período junino (alinhado a `periodo_junino_*` do dbt: 01/06 a 31/07).
FATOR_MES_JUNINO = {6: 1.30, 7: 1.18}
# Picos de São João (24/06) e São Pedro (29/06), com vizinhança.
FATOR_DATAS_PICO = {
    (6, 22): 1.20, (6, 23): 1.45, (6, 24): 1.95, (6, 25): 1.35,
    (6, 28): 1.30, (6, 29): 1.75, (6, 30): 1.25,
}  # fmt: skip
TENDENCIA_CRESCIMENTO = 0.15  # crescimento linear de 0 a +15% ao longo do período
RUIDO_DIARIO = 0.07  # desvio padrão do ruído multiplicativo por unidade/dia

# --- Distribuição por hora (horário local de Recife) ---------------------------------------
# Peso relativo por intervalo de 30 min, começando às 07:00. Picos no almoço (11:30-14:00) e no
# jantar (18:00-20:30), coerentes com os picos de `dim_hora`.
HORA_INICIAL = 7.0
PESO_MEIA_HORA = (
    1, 2, 3, 3, 2, 2, 2, 3,          # 07:00 - 10:59
    5, 9, 12, 12, 11, 8, 4, 3,       # 11:00 - 14:59 (pico do almoço)
    2.5, 3, 3.5, 4, 4, 5,            # 15:00 - 17:59
    8, 10, 11, 10, 7, 4, 2, 1,       # 18:00 - 21:59 (pico do jantar)
)  # fmt: skip

# --- Pagamento -----------------------------------------------------------------------------
PROB_FORMA = {"PIX": 0.46, "CREDITO": 0.30, "DEBITO": 0.24}
# Taxa de recusa por forma (a média ponderada fica em ~7%; crédito recusa mais).
PROB_RECUSA = {"PIX": 0.035, "CREDITO": 0.115, "DEBITO": 0.075}
# Motivos plausíveis (o gateway mock só tem os dois primeiros; os demais ampliam a análise).
MOTIVOS_RECUSA = {
    "PIX": (
        ("Pagamento recusado pelo emissor (simulação)", 0.35),
        ("PIX expirado (simulação)", 0.45),
        ("Saldo insuficiente (simulação)", 0.20),
    ),
    "CREDITO": (
        ("Pagamento recusado pelo emissor (simulação)", 0.30),
        ("Limite excedido (simulação)", 0.28),
        ("Cartão expirado (simulação)", 0.10),
        ("Suspeita de fraude (simulação)", 0.14),
        ("Token de teste desconhecido", 0.18),
    ),
    "DEBITO": (
        ("Pagamento recusado pelo emissor (simulação)", 0.30),
        ("Saldo insuficiente (simulação)", 0.50),
        ("Cartão expirado (simulação)", 0.10),
        ("Token de teste desconhecido", 0.10),
    ),
}
PROB_DESISTE_APOS_RECUSA = 0.30  # cliente desiste após uma recusa (pedido expira/cancela)
PROB_TROCA_FORMA_APOS_RECUSA = 0.45  # ao tentar de novo, troca a forma de pagamento
MAX_TENTATIVAS = 3

# --- Desfechos fora do caminho feliz (transições existentes em ALLOWED_TRANSITIONS) -----------
PROB_PARADO_AGUARDANDO = 0.012  # pedido que fica em AGUARDANDO_PAGAMENTO (sem novos eventos)
PROB_CANCELA_ANTES_PAGAR = 0.020  # AGUARDANDO_PAGAMENTO -> CANCELADO (expira em 15 min)
PROB_CANCELA_APOS_PAGAR = 0.015  # PAGO -> CANCELADO
JANELA_PAGAMENTO = timedelta(minutes=15)  # `PAYMENT_WINDOW` do domínio

# --- Tempos (segundos) ---------------------------------------------------------------------
# Preparo (EM_PREPARO -> PRONTO): lognormal com mediana de 8 min, multiplicada pela carga da hora
# (de ~0,8x fora do pico a ~1,7x no pico).
PREPARO_MEDIANA_S = 8 * 60
PREPARO_SIGMA = 0.35
PREPARO_CARGA_BASE = 0.8
PREPARO_CARGA_PICO = 0.9


# =============================================================================================
# Tipos
# =============================================================================================


@dataclass(frozen=True)
class Evento:
    """Evento de domínio antes de receber `id_sequencial` e `registrado_em`."""

    tipo_evento: str
    id_agregado: str
    payload: dict[str, Any]
    ocorrido_em: datetime  # UTC
    ordem: int  # desempate estável dentro do mesmo instante


@dataclass(frozen=True)
class Configuracao:
    semente: int = SEMENTE_PADRAO
    inicio: date = INICIO_PADRAO
    fim: date = FIM_PADRAO
    pedidos_alvo: int = PEDIDOS_ALVO_PADRAO


# =============================================================================================
# Funções puras
# =============================================================================================


def _uuid(rng: random.Random) -> uuid.UUID:
    """UUID versão 4 determinístico a partir do gerador (mesma semente, mesmo UUID)."""
    return uuid.UUID(int=rng.getrandbits(128), version=4)


def id_cliente(indice: int) -> str:
    """UUID fictício do cliente recorrente de número `indice` (determinístico)."""
    return str(uuid.uuid5(NAMESPACE, f"cliente-{indice}"))


def fator_dia(dia: date, inicio: date, fim: date) -> float:
    """Fator de volume do dia: semana, período junino, picos de São João/São Pedro e tendência."""
    fator = FATOR_DIA_SEMANA[dia.isoweekday()]
    fator *= FATOR_MES_JUNINO.get(dia.month, 1.0)
    fator *= FATOR_DATAS_PICO.get((dia.month, dia.day), 1.0)
    total = max((fim - inicio).days, 1)
    fator *= 1.0 + TENDENCIA_CRESCIMENTO * (dia - inicio).days / total
    return fator


def eh_periodo_junino(dia: date) -> bool:
    return dia.month in FATOR_MES_JUNINO


def _pesos_hora() -> tuple[list[float], list[float]]:
    inicios = [HORA_INICIAL + 0.5 * i for i in range(len(PESO_MEIA_HORA))]
    return inicios, list(PESO_MEIA_HORA)


def sortear_horario_local(rng: random.Random, dia: date) -> tuple[datetime, float]:
    """Instante local (America/Recife) do pedido e a carga relativa (0..1) da faixa de hora."""
    inicios, pesos = _pesos_hora()
    indice = rng.choices(range(len(pesos)), weights=pesos)[0]
    segundos = rng.uniform(0, 1800)
    base = datetime(dia.year, dia.month, dia.day, tzinfo=FUSO_RECIFE)
    instante = base + timedelta(hours=inicios[indice], seconds=segundos)
    return instante, pesos[indice] / max(pesos)


def _escolha(rng: random.Random, pesos: dict[str, float]) -> str:
    return rng.choices(list(pesos), weights=list(pesos.values()))[0]


def sortear_valor(rng: random.Random, canal: str, junino: bool) -> Decimal:
    """Valor total (R$, 2 casas) com ticket médio por canal (lognormal, média preservada)."""
    media = TICKET_MEDIO[canal] * (AUMENTO_TICKET_JUNINO if junino else 1.0)
    mu = math.log(media) - TICKET_SIGMA**2 / 2
    valor = Decimal(str(round(rng.lognormvariate(mu, TICKET_SIGMA), 2)))
    return max(valor, TICKET_MINIMO).quantize(Decimal("0.01"))


def sortear_cliente(rng: random.Random, canal: str) -> str | None:
    """`cliente_id` (UUID fictício) ou None; ~40% sem cliente no agregado."""
    if rng.random() < PROB_SEM_CLIENTE[canal]:
        return None
    indice = int(CLIENTES_RECORRENTES * rng.random() ** EXPOENTE_FIDELIDADE)
    return id_cliente(indice)


def _motivo(rng: random.Random, forma: str) -> str:
    motivos = MOTIVOS_RECUSA[forma]
    return rng.choices([m for m, _ in motivos], weights=[p for _, p in motivos])[0]


def simular_pedido(
    rng: random.Random,
    unidade: dict[str, Any],
    criado_local: datetime,
    carga: float,
    ordem_base: int = 0,
) -> list[Evento]:
    """Ciclo de vida de UM pedido, com eventos coerentes no tempo.

    Máquina de estados (a do domínio, `ALLOWED_TRANSITIONS`):
    AGUARDANDO_PAGAMENTO -> PAGO | CANCELADO; PAGO -> EM_PREPARO | CANCELADO;
    EM_PREPARO -> PRONTO; PRONTO -> ENTREGUE. Na criação o status é AGUARDANDO_PAGAMENTO.
    Na aprovação o domínio emite `status_pedido_alterado` (PAGO) e depois `pagamento_aprovado`.
    """
    id_pedido = str(_uuid(rng))
    canal = _escolha(rng, unidade["canais"])
    cliente = sortear_cliente(rng, canal)
    valor = sortear_valor(rng, canal, eh_periodo_junino(criado_local.date()))
    unidade_id = unidade["id"]
    contador = [ordem_base]
    eventos: list[Evento] = []

    def emitir(tipo: str, instante: datetime, payload: dict[str, Any]) -> None:
        contador[0] += 1
        eventos.append(Evento(tipo, id_pedido, payload, instante.astimezone(UTC), contador[0]))

    def mudar_status(instante: datetime, anterior: str, novo: str) -> None:
        emitir(
            "status_pedido_alterado",
            instante,
            {
                "unidade_id": unidade_id,
                "canal_pedido": canal,
                "status_anterior": anterior,
                "status_novo": novo,
            },
        )

    agora = criado_local
    emitir(
        "pedido_criado",
        agora,
        {
            "unidade_id": unidade_id,
            "cliente_id": cliente,
            "canal_pedido": canal,
            "status": "AGUARDANDO_PAGAMENTO",
            "valor_total": str(valor),
        },
    )

    if rng.random() < PROB_PARADO_AGUARDANDO:
        return eventos  # abandonado: segue AGUARDANDO_PAGAMENTO

    presencial = canal in ("BALCAO", "TOTEM")
    forma = _escolha(rng, PROB_FORMA)
    pago = False
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        agora += timedelta(seconds=rng.uniform(10, 60) if presencial else rng.uniform(25, 150))
        if agora - criado_local > JANELA_PAGAMENTO:
            break
        payload_pgto = {
            "unidade_id": unidade_id,
            "canal_pedido": canal,
            "forma_pagamento": forma,
            "valor": str(valor),
            "numero_tentativa": tentativa,
        }
        if rng.random() < PROB_RECUSA[forma]:
            emitir("pagamento_recusado", agora, {**payload_pgto, "motivo": _motivo(rng, forma)})
            if rng.random() < PROB_DESISTE_APOS_RECUSA:
                break
            if rng.random() < PROB_TROCA_FORMA_APOS_RECUSA:
                forma = _escolha(rng, PROB_FORMA)
            continue
        mudar_status(agora, "AGUARDANDO_PAGAMENTO", "PAGO")
        emitir("pagamento_aprovado", agora, payload_pgto)
        pago = True
        break

    if not pago:
        # Sem pagamento aprovado: ou expira (cancelado após a janela de 15 min) ou fica parado.
        if rng.random() < 0.55:
            expira = criado_local + JANELA_PAGAMENTO + timedelta(seconds=rng.uniform(1, 90))
            mudar_status(expira, "AGUARDANDO_PAGAMENTO", "CANCELADO")
        return eventos

    # Cancelamento após o pagamento (PAGO -> CANCELADO), antes do preparo.
    if rng.random() < PROB_CANCELA_APOS_PAGAR:
        agora += timedelta(seconds=rng.uniform(30, 240))
        mudar_status(agora, "PAGO", "CANCELADO")
        return eventos

    agora += timedelta(seconds=rng.uniform(40, 240))
    mudar_status(agora, "PAGO", "EM_PREPARO")
    preparo = rng.lognormvariate(0, PREPARO_SIGMA) * PREPARO_MEDIANA_S
    preparo *= PREPARO_CARGA_BASE + PREPARO_CARGA_PICO * carga
    agora += timedelta(seconds=max(preparo, 90))
    mudar_status(agora, "EM_PREPARO", "PRONTO")
    retirada = rng.uniform(30, 240) if presencial else rng.uniform(60, 600)
    agora += timedelta(seconds=retirada)
    mudar_status(agora, "PRONTO", "ENTREGUE")
    return eventos


def volume_do_dia(
    rng: random.Random, dia: date, base_diaria: float, peso_unidade: float, cfg: Configuracao
) -> int:
    ruido = max(0.5, rng.gauss(1.0, RUIDO_DIARIO))
    return round(base_diaria * fator_dia(dia, cfg.inicio, cfg.fim) * peso_unidade * ruido)


def gerar_eventos(cfg: Configuracao) -> list[Evento]:
    """Todos os eventos do período, em ordem cronológica de ocorrência."""
    if cfg.fim < cfg.inicio:
        raise ValueError("fim anterior ao início")
    rng = random.Random(cfg.semente)
    dias = [cfg.inicio + timedelta(days=i) for i in range((cfg.fim - cfg.inicio).days + 1)]
    soma_fatores = sum(fator_dia(d, cfg.inicio, cfg.fim) for d in dias)
    base_diaria = cfg.pedidos_alvo / soma_fatores
    eventos: list[Evento] = []
    for dia in dias:
        for unidade in UNIDADES:
            for _ in range(volume_do_dia(rng, dia, base_diaria, unidade["peso"], cfg)):
                criado, carga = sortear_horario_local(rng, dia)
                eventos.extend(simular_pedido(rng, unidade, criado, carga, len(eventos)))
    eventos.sort(key=lambda e: (e.ocorrido_em, e.ordem))
    return eventos


def para_linhas_bronze(eventos: Sequence[Evento], semente: int) -> list[dict[str, Any]]:
    """Atribui `id_evento`, `registrado_em` (= ocorrido_em + alguns ms) e `id_sequencial`.

    `id_sequencial` cresce na ordem de `registrado_em`. O `id_evento` é um UUID determinístico
    derivado da semente e da posição do evento.
    """
    rng = random.Random(f"{semente}-registro")
    linhas = []
    for evento in eventos:
        registrado = evento.ocorrido_em + timedelta(milliseconds=rng.uniform(2, 40))
        linhas.append((registrado, evento))
    linhas.sort(key=lambda par: (par[0], par[1].ordem))
    saida = []
    for sequencial, (registrado, evento) in enumerate(linhas, start=1):
        saida.append(
            {
                "id_evento": uuid.uuid5(NAMESPACE, f"evento-{semente}-{sequencial}"),
                "tipo_evento": evento.tipo_evento,
                "versao_schema": VERSAO_SCHEMA,
                "tipo_agregado": "pedido",
                "id_agregado": evento.id_agregado,
                "payload": evento.payload,
                "ocorrido_em": evento.ocorrido_em,
                "registrado_em": registrado,
                "id_sequencial": sequencial,
            }
        )
    return saida


# =============================================================================================
# I/O
# =============================================================================================


def _gravar_parquet(destino: Path, linhas: Sequence[Mapping[str, Any]]) -> None:
    """Parquet com o MESMO esquema do bronze (`BRONZE_COLUMNS`), carregado em lote via CSV.

    O `INSERT` linha a linha do extrator real é lento para ~190 mil eventos; aqui as linhas
    passam por um CSV temporário e um único `COPY`, com as mesmas colunas e tipos.
    """
    import csv
    import os

    import duckdb

    destino.parent.mkdir(parents=True, exist_ok=True)
    temp_csv = destino.with_suffix(".csv.tmp")
    temp_parquet = destino.with_suffix(".parquet.tmp")
    with temp_csv.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        for linha in linhas:
            escritor.writerow(bronze.row_to_bronze(linha))
    definicao = ", ".join(f"{nome} {tipo}" for nome, tipo in bronze.BRONZE_COLUMNS)
    conexao = duckdb.connect(":memory:")
    try:
        conexao.execute(f"CREATE TABLE lote ({definicao})")
        conexao.execute(f"COPY lote FROM '{temp_csv.as_posix()}' (FORMAT csv, HEADER false)")
        conexao.execute(f"COPY lote TO '{temp_parquet.as_posix()}' (FORMAT parquet)")
    finally:
        conexao.close()
        temp_csv.unlink(missing_ok=True)
    os.replace(temp_parquet, destino)


def gravar_lake(lake: Path, linhas: Sequence[dict[str, Any]]) -> list[Path]:
    """Grava um Parquet por partição `dt=` (data UTC de `registrado_em`), como o extrator."""
    alvo = lake / "bronze" / bronze.TABLE_NAME
    if alvo.exists():
        shutil.rmtree(alvo)  # regeração determinística: nunca mistura execuções
    bronze.ensure_empty_schema(lake)
    arquivos = []
    for dia, grupo in bronze.group_by_partition(linhas).items():
        destino = bronze.partition_path(lake, dia, "simulado")
        _gravar_parquet(destino, grupo)
        arquivos.append(destino)
    return arquivos


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera histórico sintético no formato do bronze.")
    parser.add_argument("--lake", default="data/lake_simulado", help="raiz do lake SIMULADO")
    parser.add_argument("--semente", type=int, default=SEMENTE_PADRAO)
    parser.add_argument("--inicio", type=date.fromisoformat, default=INICIO_PADRAO)
    parser.add_argument("--fim", type=date.fromisoformat, default=FIM_PADRAO)
    parser.add_argument("--pedidos", type=int, default=PEDIDOS_ALVO_PADRAO, help="volume alvo")
    parser.add_argument("--forcar", action="store_true", help="permite destino sem 'simulado'")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    lake = Path(args.lake)
    if "simulado" not in lake.name and not args.forcar:
        logger.error("Recusado: o lake de destino deve conter 'simulado' no nome (%s).", lake)
        return 2
    cfg = Configuracao(args.semente, args.inicio, args.fim, args.pedidos)
    eventos = gerar_eventos(cfg)
    linhas = para_linhas_bronze(eventos, cfg.semente)
    arquivos = gravar_lake(lake, linhas)
    pedidos = sum(1 for e in eventos if e.tipo_evento == "pedido_criado")
    por_tipo: dict[str, int] = defaultdict(int)
    for e in eventos:
        por_tipo[e.tipo_evento] += 1
    logger.info(
        "Gerados %s pedidos e %s eventos (%s) de %s a %s em %s partição(ões) de %s.",
        pedidos,
        len(eventos),
        ", ".join(f"{k}={v}" for k, v in sorted(por_tipo.items())),
        cfg.inicio,
        cfg.fim,
        len(arquivos),
        lake,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
