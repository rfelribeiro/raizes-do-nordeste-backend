"""Porta de leitura de usuários para autenticação."""

from typing import Protocol
from uuid import UUID

from raizes.application.identity.credentials import UserCredentials


class UserRepository(Protocol):
    def get_credentials_by_email(self, email: str) -> UserCredentials | None:
        """Busca sem diferenciar maiúsculas de minúsculas; `None` se não existir."""
        ...

    def is_active_customer(self, user_id: UUID) -> bool:
        """Existe, está ativo e tem perfil CLIENTE (pedido feito em nome do cliente)."""
        ...
