"""Gateway de pagamento simulado (serviço HTTP separado, D-041).

O resultado vem do token de teste. Nunca recebe nem guarda dados de cartão.
"""

import os
import time
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, StringConstraints

app = FastAPI(title="Gateway de pagamento (mock)", docs_url=None, redoc_url=None)


class Cobranca(BaseModel):
    model_config = ConfigDict(extra="ignore")

    pedidoId: UUID  # noqa: N815 (nome do contrato HTTP)
    valor: Decimal
    formaPagamento: Literal["PIX", "CREDITO", "DEBITO"]  # noqa: N815
    token: Annotated[str, StringConstraints(max_length=100)]


def _timeout_sleep_seconds() -> float:
    try:
        return float(os.environ.get("MOCK_TIMEOUT_SLEEP_SECONDS", "5"))
    except ValueError:
        return 5.0


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/cobrancas")
def cobrar(cobranca: Cobranca) -> dict[str, str]:
    token = cobranca.token
    if token == "tok_recusado":
        return {"status": "RECUSADO", "motivo": "Pagamento recusado pelo emissor (simulação)"}
    if token == "tok_timeout":
        time.sleep(_timeout_sleep_seconds())
        return {"status": "APROVADO", "idTransacao": f"txn_{uuid4().hex[:16]}"}
    if token == "tok_aprovado":
        return {"status": "APROVADO", "idTransacao": f"txn_{uuid4().hex[:16]}"}
    return {"status": "RECUSADO", "motivo": "Token de teste desconhecido"}
