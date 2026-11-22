import json
import random
import re
from datetime import UTC, date, timedelta
from pathlib import Path

import pytest

from simulacao import gerar_historico as g

CFG = g.Configuracao(semente=7, inicio=date(2026, 6, 20), fim=date(2026, 6, 26), pedidos_alvo=400)

CANAIS = {"APP", "TOTEM", "BALCAO", "PICKUP", "WEB"}
STATUS = {"AGUARDANDO_PAGAMENTO", "PAGO", "EM_PREPARO", "PRONTO", "ENTREGUE", "CANCELADO"}
FORMAS = {"PIX", "CREDITO", "DEBITO"}
TRANSICOES = {
    "AGUARDANDO_PAGAMENTO": {"PAGO", "CANCELADO"},
    "PAGO": {"EM_PREPARO", "CANCELADO"},
    "EM_PREPARO": {"PRONTO"},
    "PRONTO": {"ENTREGUE"},
    "ENTREGUE": set(),
    "CANCELADO": set(),
}
CHAVES_PII = {"nome", "cpf", "email", "e_mail", "telefone", "endereco", "data_nascimento"}


@pytest.fixture(scope="module")
def eventos() -> list[g.Evento]:
    return g.gerar_eventos(CFG)


def test_mesma_semente_mesmos_eventos(eventos: list[g.Evento]) -> None:
    outros = g.gerar_eventos(CFG)
    assert eventos == outros
    assert g.para_linhas_bronze(eventos, CFG.semente) == g.para_linhas_bronze(outros, CFG.semente)


def test_semente_diferente_muda_resultado(eventos: list[g.Evento]) -> None:
    outros = g.gerar_eventos(g.Configuracao(8, CFG.inicio, CFG.fim, CFG.pedidos_alvo))
    assert [e.id_agregado for e in eventos] != [e.id_agregado for e in outros]


def test_volume_proximo_do_alvo(eventos: list[g.Evento]) -> None:
    pedidos = sum(1 for e in eventos if e.tipo_evento == "pedido_criado")
    assert 0.7 * CFG.pedidos_alvo < pedidos < 1.4 * CFG.pedidos_alvo


def test_ciclo_coerente_no_tempo(eventos: list[g.Evento]) -> None:
    por_pedido: dict[str, list[g.Evento]] = {}
    for e in eventos:
        por_pedido.setdefault(e.id_agregado, []).append(e)
    for lista in por_pedido.values():
        lista.sort(key=lambda e: e.ordem)
        assert lista[0].tipo_evento == "pedido_criado"
        assert lista[0].payload["status"] == "AGUARDANDO_PAGAMENTO"
        instantes = [e.ocorrido_em for e in lista]
        assert instantes == sorted(instantes)
        atual = "AGUARDANDO_PAGAMENTO"
        tentativas: list[int] = []
        for e in lista[1:]:
            if e.tipo_evento == "status_pedido_alterado":
                assert e.payload["status_anterior"] == atual
                assert e.payload["status_novo"] in TRANSICOES[atual]
                atual = e.payload["status_novo"]
            else:
                tentativas.append(e.payload["numero_tentativa"])
                assert atual == "AGUARDANDO_PAGAMENTO" or e.tipo_evento == "pagamento_aprovado"
        assert tentativas == sorted(tentativas)
        # no máximo uma aprovação, sempre a última tentativa
        aprovados = [e for e in lista if e.tipo_evento == "pagamento_aprovado"]
        assert len(aprovados) <= 1


def test_valores_dentro_dos_enums(eventos: list[g.Evento]) -> None:
    for e in eventos:
        p = e.payload
        assert p["canal_pedido"] in CANAIS
        if e.tipo_evento == "pedido_criado":
            assert p["status"] in STATUS
        if e.tipo_evento == "status_pedido_alterado":
            assert {p["status_anterior"], p["status_novo"]} <= STATUS
        if "forma_pagamento" in p:
            assert p["forma_pagamento"] in FORMAS


def test_sem_pii_no_payload(eventos: list[g.Evento]) -> None:
    for e in eventos:
        assert not CHAVES_PII & set(e.payload)
        json.dumps(e.payload)  # serializável


def test_enums_iguais_ao_dominio() -> None:
    arquivo = Path(__file__).resolve().parents[2] / "src/raizes/domain/shared/enums.py"
    if not arquivo.exists():
        pytest.skip("código-fonte do domínio indisponível neste ambiente")
    texto = arquivo.read_text(encoding="utf-8")

    def valores(classe: str) -> set[str]:
        m = re.search(rf"class {classe}\(.*?(?=\nclass |\Z)", texto, re.S)
        assert m is not None
        bloco = m.group(0)
        return set(re.findall(r'= "([A-Z_]+)"', bloco))

    assert valores("OrderChannel") == CANAIS
    assert valores("OrderStatus") == STATUS
    assert valores("PaymentMethod") == FORMAS


def test_linhas_bronze_e_particao(eventos: list[g.Evento]) -> None:
    linhas = g.para_linhas_bronze(eventos, CFG.semente)
    assert [x["id_sequencial"] for x in linhas] == list(range(1, len(linhas) + 1))
    registrados = [x["registrado_em"] for x in linhas]
    assert registrados == sorted(registrados)
    assert len({x["id_evento"] for x in linhas}) == len(linhas)
    for x in linhas:
        delta = x["registrado_em"] - x["ocorrido_em"]
        assert timedelta(0) < delta < timedelta(seconds=1)
        assert x["versao_schema"] == 1
        assert x["registrado_em"].tzinfo is not None
        assert x["ocorrido_em"].utcoffset() == timedelta(0)


def test_horario_local_convertido_para_utc() -> None:
    rng = random.Random(1)
    local, _ = g.sortear_horario_local(rng, date(2026, 3, 10))
    assert local.utcoffset() == timedelta(hours=-3)
    assert 7 <= local.hour < 23
    assert local.astimezone(UTC).hour == (local.hour + 3) % 24


def test_sazonalidade() -> None:
    ini, fim = date(2026, 1, 1), date(2026, 11, 20)
    assert g.fator_dia(date(2026, 6, 24), ini, fim) > 1.5 * g.fator_dia(date(2026, 6, 17), ini, fim)
    assert g.fator_dia(date(2026, 6, 24), ini, fim) > g.fator_dia(date(2026, 3, 11), ini, fim) * 1.5
    sexta, segunda = date(2026, 3, 13), date(2026, 3, 9)
    assert g.fator_dia(sexta, ini, fim) > g.fator_dia(segunda, ini, fim)


def test_mix_por_unidade_soma_um() -> None:
    assert sum(u["peso"] for u in g.UNIDADES) == pytest.approx(1.0)
    for u in g.UNIDADES:
        assert sum(u["canais"].values()) == pytest.approx(1.0)
        assert set(u["canais"]) == CANAIS


def test_proporcao_sem_cliente_plausivel(eventos: list[g.Evento]) -> None:
    criados = [e for e in eventos if e.tipo_evento == "pedido_criado"]
    sem = sum(1 for e in criados if e.payload["cliente_id"] is None) / len(criados)
    assert 0.30 < sem < 0.50
