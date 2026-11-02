"""Tradução de erros para respostas RFC 9457 (application/problem+json)."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from raizes.application.errors import ApplicationError
from raizes.domain.shared.errors import BusinessRuleViolationError, DomainError, NotFoundError
from raizes.infrastructure.logging import request_id_var

PROBLEM_JSON = "application/problem+json"
logger = logging.getLogger(__name__)


def problem_response(
    request: Request,
    status: int,
    title: str,
    detail: str | None = None,
    **extra: Any,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "instance": request.url.path,
        "request_id": request_id_var.get(),
    }
    if detail is not None:
        body["detail"] = detail
    body.update(extra)
    return JSONResponse(jsonable_encoder(body), status_code=status, media_type=PROBLEM_JSON)


async def _not_found(request: Request, exc: Exception) -> JSONResponse:
    return problem_response(request, 404, "Recurso não encontrado", str(exc))


async def _business_rule(request: Request, exc: Exception) -> JSONResponse:
    return problem_response(request, 422, "Regra de negócio violada", str(exc))


async def _domain(request: Request, exc: Exception) -> JSONResponse:
    return problem_response(request, 422, "Erro de domínio", str(exc))


async def _application(request: Request, exc: Exception) -> JSONResponse:
    return problem_response(request, 400, "Requisição não pôde ser processada", str(exc))


async def _validation(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return problem_response(
        request,
        422,
        "Dados inválidos",
        "Um ou mais campos da requisição são inválidos.",
        errors=exc.errors(),
    )


async def _http(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    return problem_response(request, exc.status_code, str(exc.detail))


async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Erro não tratado")
    return problem_response(request, 500, "Erro interno do servidor")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(NotFoundError, _not_found)
    app.add_exception_handler(BusinessRuleViolationError, _business_rule)
    app.add_exception_handler(DomainError, _domain)
    app.add_exception_handler(ApplicationError, _application)
    app.add_exception_handler(RequestValidationError, _validation)
    app.add_exception_handler(StarletteHTTPException, _http)
    app.add_exception_handler(Exception, _unexpected)
