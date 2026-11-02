"""Health checks: liveness (processo) e readiness (dependências)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from raizes.api.dependencies import get_database_health_check
from raizes.api.errors import problem_response
from raizes.application.ports.health import DatabaseHealthCheck

router = APIRouter(prefix="/health", tags=["Saúde"])


@router.get("/live", summary="Processo vivo")
def live() -> dict[str, str]:
    return {"status": "live"}


@router.get("/ready", summary="Pronto para receber tráfego (checa o banco)", response_model=None)
def ready(
    request: Request,
    database: Annotated[DatabaseHealthCheck, Depends(get_database_health_check)],
) -> dict[str, str] | JSONResponse:
    if database.is_available():
        return {"status": "ready"}
    return problem_response(request, 503, "Serviço indisponível", "O banco de dados não respondeu.")
