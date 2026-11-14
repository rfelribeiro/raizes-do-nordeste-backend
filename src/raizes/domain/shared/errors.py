"""Erros de domínio: independentes de qualquer framework.

Cada erro carrega um `codigo` estável em MAIÚSCULAS (ex.: `ESTOQUE_INSUFICIENTE`), usado pela
camada API no campo `error` da resposta, e opcionalmente `detalhes` (um item por campo, com as
chaves `field` e `issue`).
"""

from collections.abc import Sequence


class DomainError(Exception):
    """Base de todos os erros de domínio."""

    codigo_padrao = "ERRO_DE_DOMINIO"

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


class NotFoundError(DomainError):
    """Um recurso esperado não existe."""

    codigo_padrao = "NAO_ENCONTRADO"


class BusinessRuleViolationError(DomainError):
    """Uma regra de negócio foi violada (ex.: ESTOQUE_INSUFICIENTE)."""

    codigo_padrao = "REGRA_DE_NEGOCIO_VIOLADA"
