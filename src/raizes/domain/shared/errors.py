"""Erros de domínio: independentes de qualquer framework."""


class DomainError(Exception):
    """Base de todos os erros de domínio."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """Um recurso esperado não existe."""


class BusinessRuleViolationError(DomainError):
    """Uma regra de negócio foi violada."""
