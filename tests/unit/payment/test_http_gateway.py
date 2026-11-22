import json
from decimal import Decimal
from uuid import uuid4

import httpx

from raizes.domain.shared.enums import PaymentAttemptStatus, PaymentMethod
from raizes.infrastructure.payment.http_gateway import HttpPaymentGateway


def gateway(handler: httpx.MockTransport) -> HttpPaymentGateway:
    return HttpPaymentGateway("http://gateway-mock:8001", 3.0, 2, transport=handler)


def charge(gw: HttpPaymentGateway, token: str = "tok_aprovado"):  # noqa: ANN201
    return gw.charge(uuid4(), Decimal("32.90"), PaymentMethod.PIX, token)


def test_approved() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"status": "APROVADO", "idTransacao": "txn_1"})

    result = charge(gateway(httpx.MockTransport(handler)))
    assert result.status is PaymentAttemptStatus.APROVADO
    assert result.transaction_id == "txn_1"
    assert result.calls == 1
    body = json.loads(seen[0].content)
    assert set(body) == {"pedidoId", "valor", "formaPagamento", "token"}
    assert body["valor"] == "32.90"
    assert seen[0].url.path == "/cobrancas"


def test_refused() -> None:
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, json={"status": "RECUSADO", "motivo": "sem saldo"})
    )
    result = charge(gateway(transport), "tok_recusado")
    assert result.status is PaymentAttemptStatus.RECUSADO
    assert result.refusal_reason == "sem saldo"
    assert result.calls == 1


def test_timeout_exhausted_makes_three_calls() -> None:
    count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        raise httpx.ReadTimeout("lento", request=request)

    result = charge(gateway(httpx.MockTransport(handler)), "tok_timeout")
    assert result.status is PaymentAttemptStatus.FALHA
    assert result.calls == 3
    assert count == 3


def test_recovers_on_second_call() -> None:
    count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        if count == 1:
            raise httpx.ReadTimeout("lento", request=request)
        return httpx.Response(200, json={"status": "APROVADO", "idTransacao": "txn_2"})

    result = charge(gateway(httpx.MockTransport(handler)))
    assert result.status is PaymentAttemptStatus.APROVADO
    assert result.calls == 2


def test_connection_error_is_failure_without_retry() -> None:
    count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        count += 1
        raise httpx.ConnectError("sem rota", request=request)

    result = charge(gateway(httpx.MockTransport(handler)))
    assert result.status is PaymentAttemptStatus.FALHA
    assert count == 1


def test_server_error_is_failure() -> None:
    transport = httpx.MockTransport(lambda r: httpx.Response(500, text="erro"))
    result = charge(gateway(transport))
    assert result.status is PaymentAttemptStatus.FALHA
    assert result.calls == 1
