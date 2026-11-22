"""Cliente HTTP do gateway de pagamento mock (adaptador da porta `PaymentGateway`).

Timeout de leitura por chamada; repete SOMENTE em timeout, até `max_retries` vezes. Esgotado, ou
em erro de conexão, devolve FALHA. O `token` é um token de teste; nada de cartão trafega aqui.
"""

from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx

from raizes.application.ports.payment_gateway import GatewayResult
from raizes.domain.shared.enums import PaymentAttemptStatus, PaymentMethod


class HttpPaymentGateway:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 3.0,
        max_retries: int = 2,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._max_retries = max_retries
        self._client = httpx.Client(
            base_url=base_url,
            timeout=httpx.Timeout(timeout_seconds, connect=timeout_seconds),
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def charge(
        self, order_id: UUID, amount: Decimal, method: PaymentMethod, token: str
    ) -> GatewayResult:
        body = {
            "pedidoId": str(order_id),
            "valor": str(amount),
            "formaPagamento": method.value,
            "token": token,
        }
        calls = 0
        for _ in range(1 + self._max_retries):
            calls += 1
            try:
                response = self._client.post("/cobrancas", json=body)
            except httpx.TimeoutException:
                continue  # só timeout é repetido
            except httpx.TransportError:
                return self._failure(calls, "erro de conexão com o gateway")
            return self._parse(response, calls)
        return self._failure(calls, "timeout esgotado")

    @staticmethod
    def _failure(calls: int, reason: str) -> GatewayResult:
        return GatewayResult(
            status=PaymentAttemptStatus.FALHA, calls=calls, payload={"erro": reason}
        )

    def _parse(self, response: httpx.Response, calls: int) -> GatewayResult:
        if response.status_code != 200:
            return self._failure(calls, f"gateway respondeu {response.status_code}")
        try:
            data: Any = response.json()
            status = data["status"]
        except ValueError, KeyError, TypeError:
            return self._failure(calls, "resposta inválida do gateway")
        if status == "APROVADO":
            return GatewayResult(
                status=PaymentAttemptStatus.APROVADO,
                calls=calls,
                transaction_id=data.get("idTransacao"),
                payload=data,
            )
        if status == "RECUSADO":
            return GatewayResult(
                status=PaymentAttemptStatus.RECUSADO,
                calls=calls,
                refusal_reason=data.get("motivo") or "Pagamento recusado",
                payload=data,
            )
        return self._failure(calls, "status desconhecido do gateway")
