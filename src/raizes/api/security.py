"""Dependências de autenticação e autorização por perfil (RF-03, RNF-03)."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from raizes.api.composition.identity import get_token_service
from raizes.application.errors import AuthenticationError, PermissionDeniedError
from raizes.application.ports.security import TokenService
from raizes.application.principal import Principal
from raizes.domain.shared.enums import Role

# auto_error=False: a ausência de token vira 401 no formato de erro padrão (e não o do FastAPI).
bearer_scheme = HTTPBearer(auto_error=False, bearerFormat="JWT", description="Token do login.")


def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    tokens: Annotated[TokenService, Depends(get_token_service)],
) -> Principal:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Autenticação necessária.")
    return tokens.decode(credentials.credentials)


def require_roles(*roles: Role) -> Callable[[Principal], Principal]:
    """Dependência que exige um dos perfis informados; caso contrário, 403 `SEM_PERMISSAO`."""

    def checker(principal: Annotated[Principal, Depends(get_principal)]) -> Principal:
        if not principal.has_role(*roles):
            raise PermissionDeniedError("Você não tem permissão para esta operação.")
        return principal

    return checker
