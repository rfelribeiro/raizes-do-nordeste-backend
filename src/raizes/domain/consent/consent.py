"""Consentimento (LGPD): registro append-only; o vigente é o último por finalidade."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from raizes.domain.shared.enums import ConsentAction, ConsentPurpose

# Base legal por finalidade (requisitos §7): todas as finalidades deste MVP são por consentimento.
LEGAL_BASIS = "Consentimento (LGPD art. 7º, I)"


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class Consent:
    user_id: UUID
    purpose: ConsentPurpose
    action: ConsentAction
    terms_version: str
    legal_basis: str = LEGAL_BASIS
    recorded_at: datetime = field(default_factory=_now)
    id: UUID = field(default_factory=uuid4)

    @classmethod
    def grant(
        cls, user_id: UUID, purpose: ConsentPurpose, terms_version: str, now: datetime | None = None
    ) -> Consent:
        return cls(
            user_id, purpose, ConsentAction.CONCEDIDO, terms_version, recorded_at=now or _now()
        )

    @classmethod
    def revoke(
        cls, user_id: UUID, purpose: ConsentPurpose, terms_version: str, now: datetime | None = None
    ) -> Consent:
        return cls(
            user_id, purpose, ConsentAction.REVOGADO, terms_version, recorded_at=now or _now()
        )

    @staticmethod
    def current(history: Iterable[Consent], purpose: ConsentPurpose) -> Consent | None:
        """Último registro da finalidade (None se nunca houve)."""
        records = [c for c in history if c.purpose == purpose]
        return max(records, key=lambda c: c.recorded_at) if records else None

    @staticmethod
    def is_active(history: Iterable[Consent], purpose: ConsentPurpose) -> bool:
        """Vigente = último registro é CONCEDIDO; REVOGADO ou ausência não vale."""
        latest = Consent.current(history, purpose)
        return latest is not None and latest.action is ConsentAction.CONCEDIDO

    @staticmethod
    def current_by_purpose(history: Iterable[Consent]) -> dict[ConsentPurpose, Consent]:
        result: dict[ConsentPurpose, Consent] = {}
        for c in sorted(history, key=lambda c: c.recorded_at):
            result[c.purpose] = c
        return result
