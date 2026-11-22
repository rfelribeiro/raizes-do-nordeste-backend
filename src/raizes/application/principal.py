"""Identidade autenticada da requisição (contrato compartilhado entre os módulos).

A camada API extrai o `Principal` do JWT e o entrega aos casos de uso; os casos de uso decidem
autorização e escopo (RF-03, RNF-03) a partir dele, sem conhecer HTTP nem o token.
"""

from dataclasses import dataclass
from uuid import UUID

from raizes.domain.shared.enums import Role


@dataclass(frozen=True, slots=True)
class Principal:
    """Quem está chamando.

    - `user_id`: `usuarios.id` (claim `sub` do JWT).
    - `role`: perfil no momento da emissão do token (claim `perfil`).
    - `unit_id`: unidade de lotação (claim `unidade`); obrigatória para ATENDENTE, COZINHA e
      GERENTE, nula para CLIENTE e ADMIN (D-049).
    """

    user_id: UUID
    role: Role
    unit_id: UUID | None = None

    def has_role(self, *roles: Role) -> bool:
        return self.role in roles

    def is_staff_of(self, unit_id: UUID) -> bool:
        """Colaborador lotado na unidade (escopo de unidade do RF-03)."""
        return self.unit_id is not None and self.unit_id == unit_id
