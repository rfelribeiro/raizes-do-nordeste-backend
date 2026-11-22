"""POST /pedidos/{id}/pagamentos (UC-05, D-054) com o gateway falso determinístico."""

from collections.abc import Callable
from types import ModuleType
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from tests.integration.conftest import FakeGateway
from tests.integration.helpers import API, execute, pay, post_order, query, scalar

pytestmark = pytest.mark.integration

Headers = Callable[[str], dict[str, str]]


@pytest.fixture
def order_id(client: TestClient, as_user: Headers, seeded: ModuleType) -> str:
    response = post_order(
        client, as_user("cliente"), seeded, items=[(seeded.PRODUCT_TAPIOCA_ID, 2)]
    )  # noqa: E501
    return str(response.json()["id"])


def _stock(seeded: ModuleType) -> tuple[int, int]:
    row = query(
        "SELECT qtd_disponivel, qtd_reservada FROM estoques WHERE id_produto = :p AND id_unidade = :u",  # noqa: E501
        p=seeded.PRODUCT_TAPIOCA_ID,
        u=seeded.UNIT_1_ID,
    )[0]
    return row.qtd_disponivel, row.qtd_reservada


def test_pagamento_aprovado(
    client: TestClient, as_user: Headers, seeded: ModuleType, order_id: str
) -> None:
    response = pay(client, as_user("cliente"), order_id)

    assert response.status_code == 201
    body = response.json()
    assert body["statusPedido"] == "PAGO"
    assert body["tentativa"]["status"] == "APROVADO"
    assert body["tentativa"]["numeroTentativa"] == 1
    assert body["tentativa"]["formaPagamento"] == "PIX"
    assert body["tentativa"]["valor"] == "24.00"
    assert body["tentativa"]["qtdChamadasGateway"] == 1
    assert scalar("SELECT status FROM pedidos") == "PAGO"
    # A reserva virou baixa: o reservado sai e o disponível continua descontado.
    assert _stock(seeded) == (498, 0)
    baixa = query("SELECT qtd_movimentada FROM movimentacoes_estoque WHERE tipo = 'BAIXA'")
    assert [b.qtd_movimentada for b in baixa] == [2]
    assert scalar("SELECT count(*) FROM auditoria WHERE acao = 'PAGAMENTO_APROVADO'") == 1
    assert (
        scalar("SELECT count(*) FROM outbox_eventos WHERE tipo_evento = 'pagamento_aprovado'") == 1
    )  # noqa: E501
    assert scalar("SELECT id_transacao_gateway FROM tentativas_pagamento") == "tx_fake_001"
    # histórico: criado, depois PAGO pelo sistema (sem usuário)
    assert (
        scalar("SELECT id_usuario FROM historico_status_pedido WHERE status_novo = 'PAGO'") is None
    )  # noqa: E501


def test_pagamento_recusado_mantem_pedido_e_reserva(
    client: TestClient, as_user: Headers, seeded: ModuleType, order_id: str
) -> None:
    response = pay(client, as_user("cliente"), order_id, "tok_recusado")

    assert response.status_code == 201
    body = response.json()
    assert body["tentativa"]["status"] == "RECUSADO"
    assert body["tentativa"]["motivoRecusa"] == "Saldo insuficiente"
    assert body["statusPedido"] == "AGUARDANDO_PAGAMENTO"
    assert scalar("SELECT status FROM pedidos") == "AGUARDANDO_PAGAMENTO"
    assert _stock(seeded) == (498, 2)  # reserva mantida
    assert scalar("SELECT count(*) FROM movimentacoes_estoque WHERE tipo = 'BAIXA'") == 0
    assert scalar("SELECT count(*) FROM auditoria WHERE acao = 'PAGAMENTO_RECUSADO'") == 1
    assert (
        scalar("SELECT count(*) FROM outbox_eventos WHERE tipo_evento = 'pagamento_recusado'") == 1
    )  # noqa: E501


def test_nova_tentativa_apos_recusa_e_aprovada(
    client: TestClient, as_user: Headers, order_id: str
) -> None:
    assert pay(client, as_user("cliente"), order_id, "tok_recusado").status_code == 201

    second = pay(client, as_user("cliente"), order_id)

    assert second.status_code == 201
    assert second.json()["tentativa"]["numeroTentativa"] == 2
    assert second.json()["statusPedido"] == "PAGO"
    statuses = [
        r.status for r in query("SELECT status FROM tentativas_pagamento ORDER BY numero_tentativa")
    ]  # noqa: E501
    assert statuses == ["RECUSADO", "APROVADO"]


def test_timeout_retorna_504_e_grava_falha(
    client: TestClient, as_user: Headers, seeded: ModuleType, order_id: str
) -> None:
    response = pay(client, as_user("cliente"), order_id, "tok_timeout")

    assert response.status_code == 504
    assert response.json()["error"] == "TEMPO_ESGOTADO"
    row = query("SELECT status, qtd_chamadas_gateway FROM tentativas_pagamento")[0]
    assert (row.status, row.qtd_chamadas_gateway) == ("FALHA", 3)
    assert scalar("SELECT status FROM pedidos") == "AGUARDANDO_PAGAMENTO"
    assert _stock(seeded) == (498, 2)


def test_pagar_pedido_ja_pago_409(client: TestClient, as_user: Headers, order_id: str) -> None:
    assert pay(client, as_user("cliente"), order_id).status_code == 201

    response = pay(client, as_user("cliente"), order_id)

    assert response.status_code == 409
    assert response.json()["error"] == "PEDIDO_FORA_DE_AGUARDANDO_PAGAMENTO"
    assert scalar("SELECT count(*) FROM tentativas_pagamento") == 1


def test_tentativa_pendente_bloqueia_nova_cobranca(
    client: TestClient, as_user: Headers, order_id: str, fake_gateway: FakeGateway
) -> None:
    execute(
        "INSERT INTO tentativas_pagamento (id, id_pedido, numero_tentativa, forma_pagamento, "
        "status, valor) SELECT :id, id, 1, 'PIX', 'PENDENTE', valor_total FROM pedidos",
        id=uuid4(),
    )

    response = pay(client, as_user("cliente"), order_id)

    assert response.status_code == 409
    assert response.json()["error"] == "PAGAMENTO_EM_ANDAMENTO"
    assert fake_gateway.calls == []


def test_pedido_de_outro_cliente_404(
    client: TestClient, as_user: Headers, order_id: str, fake_gateway: FakeGateway
) -> None:
    response = pay(client, as_user("cliente2"), order_id)

    assert response.status_code == 404
    assert fake_gateway.calls == []


def test_colaborador_nao_paga_403(client: TestClient, as_user: Headers, order_id: str) -> None:
    for user in ("atendente", "gerente", "cozinha", "admin"):
        assert pay(client, as_user(user), order_id).status_code == 403, user


def test_corpo_invalido_422(client: TestClient, as_user: Headers, order_id: str) -> None:
    response = client.post(
        f"{API}/pedidos/{order_id}/pagamentos",
        json={"formaPagamento": "CHEQUE"},
        headers=as_user("cliente"),
    )

    assert response.status_code == 422


def test_pedido_inexistente_404(client: TestClient, as_user: Headers, seeded: ModuleType) -> None:
    assert pay(client, as_user("cliente"), str(uuid4())).status_code == 404


def test_pedido_cancelado_durante_a_cobranca_gera_409_e_audita_divergencia(
    client: TestClient, as_user: Headers, order_id: str, fake_gateway: FakeGateway
) -> None:
    def cancel(order: UUID) -> None:
        execute("UPDATE pedidos SET status = 'CANCELADO' WHERE id = :id", id=order)

    fake_gateway.on_charge = cancel

    response = pay(client, as_user("cliente"), order_id)

    assert response.status_code == 409
    assert response.json()["error"] == "PAGAMENTO_DIVERGENTE"
    assert scalar("SELECT status FROM tentativas_pagamento") == "APROVADO"  # resultado do gateway
    assert scalar("SELECT count(*) FROM auditoria WHERE acao = 'PAGAMENTO_DIVERGENTE'") == 1
    assert scalar("SELECT count(*) FROM movimentacoes_estoque WHERE tipo = 'BAIXA'") == 0
