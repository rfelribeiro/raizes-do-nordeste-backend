"""Middleware ASGI: X-Request-ID (gera se ausente) e log de acesso."""

import logging
import re
import time
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from raizes.infrastructure.logging import request_id_var

HEADER_NAME = "X-Request-ID"
_VALID_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
logger = logging.getLogger("raizes.access")


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get(HEADER_NAME)
        request_id = incoming if incoming and _VALID_ID.match(incoming) else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        # Disponível em request.state (inclusive para o handler do 500, que roda fora deste escopo).
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.perf_counter()
        status_code = 500

        async def send_with_header(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[HEADER_NAME] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            logger.info(
                "requisição concluída",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status_code": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            request_id_var.reset(token)
