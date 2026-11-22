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


class AuthenticationError(ApplicationError):
    """Credenciais ou token ausentes, inválidos ou expirados (401)."""

    codigo_padrao = "NAO_AUTENTICADO"


class PermissionDeniedError(ApplicationError):
    """Usuário autenticado sem permissão para a operação (403)."""

    codigo_padrao = "SEM_PERMISSAO"


class ConflictError(ApplicationError):
    """A operação conflita com o estado atual do recurso (409)."""

    codigo_padrao = "CONFLITO"


class ApplicationValidationError(ApplicationError):
    """Entrada inválida detectada na aplicação, com `detalhes` por campo (422)."""

    codigo_padrao = "VALIDACAO_FALHOU"


class DependencyTimeoutError(ApplicationError):
    """Dependência externa não respondeu no tempo limite, após as novas tentativas (504)."""

    codigo_padrao = "TEMPO_ESGOTADO"
