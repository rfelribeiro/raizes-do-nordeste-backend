"""Erros da camada de aplicação (falhas de orquestração de casos de uso)."""

from collections.abc import Sequence


class ApplicationError(Exception):
    """Base dos erros da camada de aplicação."""

    codigo_padrao = "REQUISICAO_INVALIDA"

    def __init__(
        self,
        message: str,
        *,
        codigo: str | None = None,
        detalhes: Sequence[dict[str, str]] = (),
    ) -> None:
        super().__init__(message)
        self.message = message
        self.codigo = codigo or self.codigo_padrao
        self.detalhes = list(detalhes)
