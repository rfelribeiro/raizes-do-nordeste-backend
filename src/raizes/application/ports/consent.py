"""Porta de persistência de consentimentos (append-only)."""

from typing import Protocol
from uuid import UUID

from raizes.domain.consent.consent import Consent


class ConsentRepository(Protocol):
    def history(self, user_id: UUID) -> list[Consent]:
        """Todos os registros do usuário, do mais antigo ao mais recente."""
        ...

    def add(self, consent: Consent) -> None: ...
