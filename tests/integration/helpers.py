"""Ajudantes compartilhados pelos testes de integração."""

from types import ModuleType
from typing import Any

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import text

from raizes.infrastructure.db.session import get_engine

API = "/api/v1"


def query(sql: str, **params: Any) -> list[Any]:
    """Consulta direta ao banco de testes (para conferir efeitos colaterais)."""
    with get_engine().connect() as connection:
        return list(connection.execute(text(sql), params).all())


def scalar(sql: str, **params: Any) -> Any:
    with get_engine().connect() as connection:
        return connection.execute(text(sql), params).scalar()


def execute(sql: str, **params: Any) -> None:
    with get_engine().begin() as connection:
        connection.execute(text(sql), params)


def post_order(
    client: TestClient,
    headers: dict[str, str],
    seed: ModuleType,
    *,
    channel: str | None = "APP",
    unit: Any = None,
    items: list[tuple[Any, int]] | None = None,
    extra: dict[str, Any] | None = None,
) -> Response:
    body: dict[str, Any] = {
        "unidadeId": str(unit or seed.UNIT_1_ID),
        "itens": [
            {"produtoId": str(pid), "quantidade": qty}
            for pid, qty in (items or [(seed.PRODUCT_TAPIOCA_ID, 2)])
        ],
    }
    if channel is not None:
        body["canalPedido"] = channel
    body.update(extra or {})
    return client.post(f"{API}/pedidos", json=body, headers=headers)


def pay(
    client: TestClient, headers: dict[str, str], order_id: str, token: str = "tok_aprovado"
) -> Response:
    return client.post(
        f"{API}/pedidos/{order_id}/pagamentos",
        json={"formaPagamento": "PIX", "tokenPagamento": token},
        headers=headers,
    )
