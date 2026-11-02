"""Erros da camada de aplicação (falhas de orquestração de casos de uso)."""


class ApplicationError(Exception):
    """Base dos erros da camada de aplicação."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
