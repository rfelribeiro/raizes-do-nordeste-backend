"""Ponto de entrada: factory da aplicação FastAPI (composição das camadas)."""

from fastapi import FastAPI

from raizes.api import health
from raizes.api.errors import register_error_handlers
from raizes.api.middleware import RequestIdMiddleware
from raizes.api.schemas.erro import RESPOSTAS_DE_ERRO
from raizes.api.v1.router import router as v1_router
from raizes.infrastructure.config import get_settings
from raizes.infrastructure.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging(get_settings().app_log_level)
    app = FastAPI(
        title="Raízes do Nordeste - API",
        version="0.1.0",
        description="API back-end da rede de lanchonetes Raízes do Nordeste (projeto acadêmico).",
        responses=RESPOSTAS_DE_ERRO,
    )
    app.add_middleware(RequestIdMiddleware)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(v1_router)
    return app
