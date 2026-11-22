"""POST /pedidos (UC-04): criação, perfil x canal, reserva e 409 sem efeito colateral."""

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from types import ModuleType
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.integration.helpers import API, post_order, query, scalar

pytestmark = pytest.mark.integration

Headers = Callable[[str], dict[str, str]]


def test_cliente_cria_pedido_e_reserva_estoque(
    client: TestClient, as_user: Headers, seeded: ModuleType
) -> None:
    response = post_order(
        client, as_user("cliente"), seeded, items=[(seeded.PRODUCT_TAPIOCA_ID, 2)]
    )  # noqa: E501

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "AGUARDANDO_PAGAMENTO"
    assert body["canalPedido"] == "APP"
    assert body["clienteId"] == str(seeded.CLIENT_1_ID)
    assert body["unidadeId"] == str(seeded.UNIT_1_ID)
    assert isinstance(body["numeroPedido"], int)
    assert body["valorItens"] == "24.00"
    assert body["valorDesconto"] == "0.00"
    assert body["valorTotal"] == "24.00"
    assert body["itens"][0]["precoUnitario"] == "12.00"
    assert body["itens"][0]["valorTotalItem"] == "24.00"
    assert response.headers["Location"].endswith(body["id"])

    stock = query(
        "SELECT qtd_disponivel, qtd_reservada FROM estoques WHERE id_produto = :p AND id_unidade = :u",  # noqa: E501
        p=seeded.PRODUCT_TAPIOCA_ID,
        u=seeded.UNIT_1_ID,
    )[0]
    assert (stock.qtd_disponivel, stock.qtd_reservada) == (498, 2)
    movement = query(
        "SELECT tipo, qtd_movimentada, id_pedido FROM movimentacoes_estoque WHERE tipo = 'RESERVA'"
    )  # noqa: E501
    assert [(m.qtd_movimentada, str(m.id_pedido)) for m in movement] == [(2, body["id"])]
    assert scalar("SELECT count(*) FROM historico_status_pedido") == 1
    assert scalar("SELECT count(*) FROM auditoria WHERE acao = 'PEDIDO_CRIADO'") == 1
    assert scalar("SELECT count(*) FROM outbox_eventos WHERE tipo_evento = 'pedido_criado'") == 1


def test_preco_local_do_cardapio_e_congelado(
    client: TestClient, as_user: Headers, seeded: ModuleType
) -> None:
    response = post_order(client, as_user("cliente"), seeded, items=[(seeded.PRODUCT_CUSCUZ_ID, 1)])

    assert response.status_code == 201
    assert (
        response.json()["itens"][0]["precoUnitario"] == "11.00"
    )  # local, não os 10.50 de referência  # noqa: E501
    stored = scalar("SELECT valor_preco_unitario FROM itens_pedido")
    assert stored == Decimal("11.00")


def test_atendente_cria_no_balcao_para_cliente_identificado(
    client: TestClient, as_user: Headers, seeded: ModuleType
) -> None:
    response = post_order(
        client,
        as_user("atendente"),
        seeded,
        channel="BALCAO",
        extra={"clienteId": str(seeded.CLIENT_2_ID)},
    )

    assert response.status_code == 201
    assert response.json()["clienteId"] == str(seeded.CLIENT_2_ID)
    assert response.json()["canalPedido"] == "BALCAO"


def test_atendente_cria_sem_cliente_identificado(
    client: TestClient, as_user: Headers, seeded: ModuleType
) -> None:
    response = post_order(client, as_user("atendente"), seeded, channel="TOTEM")

    assert response.status_code == 201
    assert response.json()["clienteId"] is None


def test_cliente_nao_cria_para_outro_cliente(
    client: TestClient, as_user: Headers, seeded: ModuleType
) -> None:
    response = post_order(
        client, as_user("cliente"), seeded, extra={"clienteId": str(seeded.CLIENT_2_ID)}
    )

    assert response.status_code == 201
    assert response.json()["clienteId"] == str(seeded.CLIENT_1_ID)


def test_canal_ausente_retorna_422(
    client: TestClient, as_user: Headers, seeded: ModuleType
) -> None:  # noqa: E501
    response = post_order(client, as_user("cliente"), seeded, channel=None)

    assert response.status_code == 422
    assert response.json()["error"] == "VALIDACAO_FALHOU"
    assert any(d["field"] == "canalPedido" for d in response.json()["details"])
    assert scalar("SELECT count(*) FROM pedidos") == 0


def test_canal_invalido_retorna_422(
    client: TestClient, as_user: Headers, seeded: ModuleType
) -> None:  # noqa: E501
    response = post_order(client, as_user("cliente"), seeded, channel="CARRIER_PIGEON")

    assert response.status_code == 422
    assert any(d["field"] == "canalPedido" for d in response.json()["details"])


@pytest.mark.parametrize(("user", "channel"), [("cliente", "BALCAO"), ("atendente", "APP")])
def test_canal_incompativel_com_o_perfil_retorna_422(
    client: TestClient, as_user: Headers, seeded: ModuleType, user: str, channel: str
) -> None:
    response = post_order(client, as_user(user), seeded, channel=channel)

    assert response.status_code == 422
    assert response.json()["details"][0]["field"] == "canalPedido"
    assert scalar("SELECT count(*) FROM pedidos") == 0


def test_cozinha_nao_cria_pedido_403(
    client: TestClient, as_user: Headers, seeded: ModuleType
) -> None:
    response = post_order(client, as_user("cozinha"), seeded, channel="BALCAO")

    assert response.status_code == 403
    assert response.json()["error"] == "SEM_PERMISSAO"


def test_perfil_e_checado_antes_do_canal(client: TestClient, as_user: Headers) -> None:
    response = client.post(f"{API}/pedidos", json={}, headers=as_user("cozinha"))

    assert response.status_code == 403


def test_colaborador_de_outra_unidade_403(
    client: TestClient, as_user: Headers, seeded: ModuleType
) -> None:
    response = post_order(
        client, as_user("gerente2"), seeded, channel="BALCAO", unit=seeded.UNIT_1_ID
    )  # noqa: E501

    assert response.status_code == 403


def test_sem_token_401(client: TestClient, seeded: ModuleType) -> None:
    response = client.post(f"{API}/pedidos", json={})

    assert response.status_code == 401


def test_estoque_insuficiente_409_sem_efeito_colateral(
    client: TestClient, as_user: Headers, seeded: ModuleType
) -> None:
    # Tapioca (500 em estoque) + carne de sol (só 2): o segundo item derruba o pedido inteiro.
    response = post_order(
        client,
        as_user("cliente"),
        seeded,
        items=[(seeded.PRODUCT_TAPIOCA_ID, 1), (seeded.PRODUCT_CARNE_SOL_ID, 3)],
    )

    assert response.status_code == 409
    assert response.json()["error"] == "ESTOQUE_INSUFICIENTE"
    assert scalar("SELECT count(*) FROM pedidos") == 0
    assert scalar("SELECT count(*) FROM itens_pedido") == 0
    assert scalar("SELECT count(*) FROM historico_status_pedido") == 0
    assert scalar("SELECT count(*) FROM auditoria") == 0
    assert scalar("SELECT count(*) FROM outbox_eventos") == 0
    assert scalar("SELECT count(*) FROM movimentacoes_estoque WHERE tipo = 'RESERVA'") == 0
    assert scalar("SELECT sum(qtd_reservada) FROM estoques") == 0
    assert (
        scalar(
            "SELECT qtd_disponivel FROM estoques WHERE id_produto = :p AND id_unidade = :u",
            p=seeded.PRODUCT_CARNE_SOL_ID,
            u=seeded.UNIT_1_ID,
        )
        == 2
    )


def test_unidade_inexistente_404(client: TestClient, as_user: Headers, seeded: ModuleType) -> None:
    response = post_order(client, as_user("cliente"), seeded, unit=uuid4())

    assert response.status_code == 404


def test_produto_inexistente_404(client: TestClient, as_user: Headers, seeded: ModuleType) -> None:
    response = post_order(client, as_user("cliente"), seeded, items=[(uuid4(), 1)])

    assert response.status_code == 404


def test_produto_nao_ofertado_na_unidade_422(
    client: TestClient, as_user: Headers, seeded: ModuleType
) -> None:
    # A unidade REDUZIDA não oferta carne de sol.
    response = post_order(
        client,
        as_user("cliente"),
        seeded,
        unit=seeded.UNIT_2_ID,
        items=[(seeded.PRODUCT_CARNE_SOL_ID, 1)],
    )

    assert response.status_code == 422
    assert response.json()["error"] == "PRODUTO_NAO_OFERTADO"


def test_produto_sazonal_fora_do_periodo_422(
    client: TestClient, as_user: Headers, seeded: ModuleType
) -> None:
    today = datetime.now(UTC).date()
    if seeded.SEASON_START <= today <= seeded.SEASON_END:
        pytest.skip("hoje está dentro do período sazonal da carga inicial")
    response = post_order(
        client, as_user("cliente"), seeded, items=[(seeded.PRODUCT_CANJICA_ID, 1)]
    )

    assert response.status_code == 422
    assert response.json()["error"] == "PRODUTO_INDISPONIVEL"


def test_quantidade_invalida_422(client: TestClient, as_user: Headers, seeded: ModuleType) -> None:
    response = post_order(
        client, as_user("cliente"), seeded, items=[(seeded.PRODUCT_TAPIOCA_ID, 0)]
    )

    assert response.status_code == 422
