import time

import pytest
from fastapi.testclient import TestClient

from gateway_mock.app import app

client = TestClient(app)
BODY = {
    "pedidoId": "6f1c4a7e-0b1d-4d57-9a0e-7b8f3a2c1d00",
    "valor": "32.90",
    "formaPagamento": "PIX",
}


def test_health() -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_approved() -> None:
    response = client.post("/cobrancas", json={**BODY, "token": "tok_aprovado"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "APROVADO"
    assert data["idTransacao"]


def test_refused() -> None:
    data = client.post("/cobrancas", json={**BODY, "token": "tok_recusado"}).json()
    assert data["status"] == "RECUSADO"
    assert data["motivo"]


def test_unknown_token_is_refused() -> None:
    data = client.post("/cobrancas", json={**BODY, "token": "tok_xyz"}).json()
    assert data == {"status": "RECUSADO", "motivo": "Token de teste desconhecido"}


def test_timeout_token_sleeps_then_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOCK_TIMEOUT_SLEEP_SECONDS", "0.2")
    start = time.monotonic()
    response = client.post("/cobrancas", json={**BODY, "token": "tok_timeout"})
    assert time.monotonic() - start >= 0.2
    assert response.status_code == 200


def test_invalid_body_is_422() -> None:
    assert client.post("/cobrancas", json={"token": "tok_aprovado"}).status_code == 422
