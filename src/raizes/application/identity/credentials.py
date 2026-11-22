"""Credenciais de um usuário, como lidas do repositório para autenticação."""

from dataclasses import dataclass
from uuid import UUID

from raizes.domain.shared.enums import Role


@dataclass(frozen=True, slots=True)
class UserCredentials:
    user_id: UUID
    role: Role
    unit_id: UUID | None
    password_hash: str
    is_active: bool
