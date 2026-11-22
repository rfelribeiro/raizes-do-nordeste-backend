"""Porta de leitura de usuários para autenticação."""

from typing import Protocol

from raizes.application.identity.credentials import UserCredentials


class UserRepository(Protocol):
    def get_credentials_by_email(self, email: str) -> UserCredentials | None:
        """Busca sem diferenciar maiúsculas de minúsculas; `None` se não existir."""
        ...
