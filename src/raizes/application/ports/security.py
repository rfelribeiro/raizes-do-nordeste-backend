"""Portas de segurança: hash de senha e emissão/validação de token de acesso."""

from dataclasses import dataclass
from typing import Protocol

from raizes.application.principal import Principal


@dataclass(frozen=True, slots=True)
class IssuedToken:
    access_token: str
    expires_in: int  # segundos


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool:
        """True se a senha confere; False caso contrário (nunca levanta por senha errada)."""
        ...


class TokenService(Protocol):
    def issue(self, principal: Principal) -> IssuedToken: ...

    def decode(self, token: str) -> Principal:
        """Valida o token e devolve o `Principal`; levanta `AuthenticationError` se inválido."""
        ...
