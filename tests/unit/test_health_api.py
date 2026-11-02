import pytest
from fastapi.testclient import TestClient

from raizes.api.dependencies import get_database_health_check
from raizes.application.errors import ApplicationError
from raizes.domain.shared.errors import BusinessRuleViolationError, NotFoundError
from raizes.main import create_app


class FakeHealth:
    def __init__(self, available: bool) -> None:
        self.available = available

    def is_available(self) -> bool:
        return self.available


def _client(available: bool) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_database_health_check] = lambda: FakeHealth(available)
    return TestClient(app)


def test_live_returns_200() -> None:
    response = _client(True).get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "live"}


def test_ready_ok_when_database_available() -> None:
    response = _client(True).get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_503_problem_json_when_database_down() -> None:
    response = _client(False).get("/health/ready")
    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["status"] == 503


def test_request_id_is_generated_and_echoed() -> None:
    client = _client(True)
    generated = client.get("/health/live").headers["X-Request-ID"]
    assert len(generated) == 32
    echoed = client.get("/health/live", headers={"X-Request-ID": "abc-123"})
    assert echoed.headers["X-Request-ID"] == "abc-123"


def test_unsafe_request_id_is_replaced() -> None:
    response = _client(True).get("/health/live", headers={"X-Request-ID": "id com espaco"})
    assert response.headers["X-Request-ID"] != "id com espaco"


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (NotFoundError("x"), 404),
        (BusinessRuleViolationError("x"), 422),
        (ApplicationError("x"), 400),
        (RuntimeError("x"), 500),
    ],
)
def test_errors_become_problem_json(error: Exception, status: int) -> None:
    app = create_app()

    @app.get("/_boom")
    def boom() -> None:
        raise error

    response = TestClient(app, raise_server_exceptions=False).get("/_boom")
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["instance"] == "/_boom"


def test_unknown_route_is_problem_json() -> None:
    response = _client(True).get("/nao-existe")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
