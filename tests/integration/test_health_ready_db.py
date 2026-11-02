import pytest
from fastapi.testclient import TestClient

from raizes.main import create_app

pytestmark = pytest.mark.integration


def test_ready_against_real_postgres() -> None:
    response = TestClient(create_app()).get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
