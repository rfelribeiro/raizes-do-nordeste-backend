"""Tradução de TODOS os erros para o formato padrão do roteiro (ADR 0011).

Corpo `application/json`: `error`, `message`, `details[{field, issue}]`, `timestamp`, `path`,
`requestId`. Cobre erros de domínio e de aplicação, HTTPException (inclui 404 de rota
inexistente e 405), validação de entrada (422) e falhas inesperadas (500, sem vazar detalhes).
"""

import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from raizes.api.schemas.erro import DetalheErro, ErroPadrao
from raizes.application.errors import ApplicationError
from raizes.domain.shared.errors import BusinessRuleViolationError, DomainError, NotFoundError
from raizes.infrastructure.logging import request_id_var

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"

# Código e mensagem em português por status HTTP (usados para HTTPException sem detalhe próprio).
_CODIGOS: dict[int, tuple[str, str]] = {
    400: ("REQUISICAO_INVALIDA", "A requisição é inválida."),
    401: ("NAO_AUTENTICADO", "Autenticação necessária."),
    403: ("SEM_PERMISSAO", "Você não tem permissão para esta operação."),
    404: ("NAO_ENCONTRADO", "Recurso não encontrado."),
    405: ("METODO_NAO_PERMITIDO", "Método HTTP não permitido para esta rota."),
    409: ("CONFLITO", "A operação conflita com o estado atual do recurso."),
    422: ("VALIDACAO_FALHOU", "Um ou mais campos da requisição são inválidos."),
    429: ("MUITAS_REQUISICOES", "Muitas requisições; tente novamente mais tarde."),
    503: ("SERVICO_INDISPONIVEL", "Serviço temporariamente indisponível."),
}


def erro_response(
    request: Request,
    status: int,
    code: str,
    message: str,
    details: Sequence[Mapping[str, str]] = (),
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Monta a resposta de erro padrão. `requestId` vem do escopo (vale também para o 500)."""
    request_id = getattr(request.state, "request_id", None) or request_id_var.get()
    body = ErroPadrao(
        error=code,
        message=message,
        details=[DetalheErro(field=d["field"], issue=d["issue"]) for d in details],
        timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        path=request.url.path,
        request_id=request_id,
    )
    response_headers = dict(headers or {})
    if request_id:
        response_headers[REQUEST_ID_HEADER] = request_id
    return JSONResponse(
        body.model_dump(by_alias=True, mode="json"),
        status_code=status,
        headers=response_headers,
    )


def formatar_loc(loc: Sequence[Any]) -> str:
    """`("body", "itens", 0, "quantidade")` -> `itens[0].quantidade` (sem o prefixo `body`)."""
    partes = list(loc)
    if partes and partes[0] == "body":
        partes = partes[1:]
    caminho = ""
    for parte in partes:
        if isinstance(parte, int):
            caminho += f"[{parte}]"
        else:
            caminho += f".{parte}" if caminho else str(parte)
    return caminho


async def _not_found(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, NotFoundError)
    return erro_response(request, 404, exc.codigo, exc.message, exc.detalhes)


async def _business_rule(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, BusinessRuleViolationError)
    return erro_response(request, 409, exc.codigo, exc.message, exc.detalhes)


async def _domain(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    return erro_response(request, 422, exc.codigo, exc.message, exc.detalhes)


async def _application(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApplicationError)
    return erro_response(request, 400, exc.codigo, exc.message, exc.detalhes)


async def _validation(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = [
        {"field": formatar_loc(err["loc"]), "issue": str(err["msg"])} for err in exc.errors()
    ]
    code, message = _CODIGOS[422]
    return erro_response(request, 422, code, message, details)


async def _http(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code, message = _CODIGOS.get(
        exc.status_code, ("ERRO_HTTP", "A requisição não pôde ser atendida.")
    )
    # Mantém um detalhe próprio da aplicação; ignora a frase padrão (inglês) do Starlette.
    padrao = HTTPStatus(exc.status_code).phrase if exc.status_code in HTTPStatus else None
    if isinstance(exc.detail, str) and exc.detail and exc.detail != padrao:
        message = exc.detail
    return erro_response(request, exc.status_code, code, message, headers=exc.headers)


async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Erro não tratado", exc_info=exc)
    return erro_response(request, 500, "ERRO_INTERNO", "Erro interno do servidor.")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(NotFoundError, _not_found)
    app.add_exception_handler(BusinessRuleViolationError, _business_rule)
    app.add_exception_handler(DomainError, _domain)
    app.add_exception_handler(ApplicationError, _application)
    app.add_exception_handler(RequestValidationError, _validation)
    app.add_exception_handler(StarletteHTTPException, _http)
    app.add_exception_handler(Exception, _unexpected)
