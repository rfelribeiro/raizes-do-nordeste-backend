"""Formato padrão de erro do roteiro (ADR 0011): todas as falhas saem como ErroPadrao."""

from typing import Annotated

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from raizes.api.errors import formatar_loc
from raizes.application.errors import ApplicationError
from raizes.domain.shared.errors import BusinessRuleViolationError, NotFoundError
from raizes.main import create_app

CAMPOS = {"error", "message", "details", "timestamp", "path", "requestId"}


class ItemEntrada(BaseModel):
    quantidade: Annotated[int, Field(gt=0)]


class PedidoEntrada(BaseModel):
    itens: list[ItemEntrada]


def _app() -> FastAPI:
    app = create_app()

    @app.post("/_pedidos")
    def criar(pedido: PedidoEntrada) -> None:
        return None

    @app.get("/_sem-estoque")
    def sem_estoque() -> None:
        raise BusinessRuleViolationError(
            "Não há quantidade suficiente para um ou mais itens.",
            codigo="ESTOQUE_INSUFICIENTE",
            detalhes=[{"field": "itens[0].quantidade", "issue": "Disponível: 1"}],
        )

    @app.get("/_proibido")
    def proibido() -> None:
        raise HTTPException(status_code=403)

    @app.get("/_explode")
    def explode() -> None:
        raise RuntimeError("segredo interno: senha=abc123")

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_app(), raise_server_exceptions=False)


def _assert_formato(response_json: dict[str, object], path: str) -> None:
    assert set(response_json) == CAMPOS
    assert response_json["path"] == path
    assert str(response_json["timestamp"]).endswith("Z")


def test_rota_inexistente_404(client: TestClient) -> None:
    response = client.get("/nao-existe", headers={"X-Request-ID": "req-1"})
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    _assert_formato(body, "/nao-existe")
    assert body["error"] == "NAO_ENCONTRADO"
    assert body["requestId"] == "req-1"
    assert body["details"] == []


def test_json_malformado_400(client: TestClient) -> None:
    response = client.post(
        "/_pedidos", content=b'{"itens": [', headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400
    body = response.json()
    _assert_formato(body, "/_pedidos")
    assert body["error"] == "REQUISICAO_INVALIDA"
    assert body["details"] == []


def test_campo_ausente_continua_422(client: TestClient) -> None:
    response = client.post("/_pedidos", json={})
    assert response.status_code == 422
    assert response.json()["error"] == "VALIDACAO_FALHOU"


def test_metodo_nao_permitido_405(client: TestClient) -> None:
    response = client.delete("/health/live")
    assert response.status_code == 405
    assert response.json()["error"] == "METODO_NAO_PERMITIDO"
    assert "allow" in response.headers


def test_http_exception_403(client: TestClient) -> None:
    response = client.get("/_proibido")
    assert response.status_code == 403
    assert response.json()["error"] == "SEM_PERMISSAO"


def test_validacao_422_com_details_por_campo(client: TestClient) -> None:
    response = client.post("/_pedidos", json={"itens": [{"quantidade": 0}]})
    assert response.status_code == 422
    body = response.json()
    _assert_formato(body, "/_pedidos")
    assert body["error"] == "VALIDACAO_FALHOU"
    assert [d["field"] for d in body["details"]] == ["itens[0].quantidade"]
    assert body["details"][0]["issue"]


def test_erro_de_dominio_mapeado_com_codigo_proprio(client: TestClient) -> None:
    response = client.get("/_sem-estoque")
    assert response.status_code == 409
    body = response.json()
    _assert_formato(body, "/_sem-estoque")
    assert body["error"] == "ESTOQUE_INSUFICIENTE"
    assert body["details"] == [{"field": "itens[0].quantidade", "issue": "Disponível: 1"}]


@pytest.mark.parametrize(
    ("error", "status", "codigo"),
    [
        (NotFoundError("x"), 404, "NAO_ENCONTRADO"),
        (BusinessRuleViolationError("x"), 409, "REGRA_DE_NEGOCIO_VIOLADA"),
        (ApplicationError("x"), 400, "REQUISICAO_INVALIDA"),
    ],
)
def test_erros_padrao_de_dominio_e_aplicacao(error: Exception, status: int, codigo: str) -> None:
    app = create_app()

    @app.get("/_boom")
    def boom() -> None:
        raise error

    response = TestClient(app).get("/_boom")
    assert response.status_code == status
    assert response.json()["error"] == codigo


def test_500_nao_vaza_detalhes_internos_e_tem_request_id(client: TestClient) -> None:
    response = client.get("/_explode", headers={"X-Request-ID": "req-500"})
    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    _assert_formato(body, "/_explode")
    assert body["error"] == "ERRO_INTERNO"
    assert body["requestId"] == "req-500"
    assert "segredo" not in response.text
    assert "abc123" not in response.text
    assert "Traceback" not in response.text


def test_request_id_gerado_quando_ausente(client: TestClient) -> None:
    body = client.get("/nao-existe").json()
    assert body["requestId"]


def test_openapi_documenta_erro_padrao(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert {"ErroPadrao", "DetalheErro"} <= set(spec["components"]["schemas"])
    respostas = spec["paths"]["/health/live"]["get"]["responses"]
    for status in ("400", "401", "403", "404", "409", "422", "500"):
        ref = respostas[status]["content"]["application/json"]["schema"]["$ref"]
        assert ref.endswith("/ErroPadrao")


@pytest.mark.parametrize(
    ("loc", "esperado"),
    [
        (("body", "itens", 0, "quantidade"), "itens[0].quantidade"),
        (("body", "canalPedido"), "canalPedido"),
        (("query", "page"), "query.page"),
        (("body",), ""),
    ],
)
def test_formatar_loc(loc: tuple[str | int, ...], esperado: str) -> None:
    assert formatar_loc(loc) == esperado
