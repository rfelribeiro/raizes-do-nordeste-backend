"""UC-09 Gerir Consentimento (LGPD): registro append-only; o vigente é o último por finalidade."""

from dataclasses import dataclass

from raizes.application.errors import ConflictError, PermissionDeniedError
from raizes.application.ports.audit import AuditEntry, AuditRecorder
from raizes.application.ports.consent import ConsentRepository
from raizes.application.ports.unit_of_work import UnitOfWork
from raizes.application.principal import Principal
from raizes.domain.consent.consent import Consent
from raizes.domain.shared.enums import ConsentAction, ConsentPurpose, Role


def _only_customer(principal: Principal) -> None:
    if principal.role is not Role.CLIENTE:
        raise PermissionDeniedError("Só o cliente gerencia os próprios consentimentos.")


class RegisterConsent:
    def __init__(self, consents: ConsentRepository, audit: AuditRecorder, uow: UnitOfWork) -> None:
        self._consents = consents
        self._audit = audit
        self._uow = uow

    def execute(
        self,
        principal: Principal,
        purpose: ConsentPurpose,
        action: ConsentAction,
        terms_version: str,
    ) -> Consent:
        _only_customer(principal)
        active = Consent.is_active(self._consents.history(principal.user_id), purpose)
        if action is ConsentAction.CONCEDIDO:
            if active:
                raise ConflictError(
                    "A finalidade já está concedida.", codigo="CONSENTIMENTO_JA_CONCEDIDO"
                )
            consent = Consent.grant(principal.user_id, purpose, terms_version)
        else:
            if not active:
                raise ConflictError(
                    "Não há consentimento vigente para revogar.",
                    codigo="CONSENTIMENTO_SEM_VIGENTE",
                )
            consent = Consent.revoke(principal.user_id, purpose, terms_version)
        self._consents.add(consent)
        self._audit.record(
            AuditEntry(
                action="CONSENTIMENTO_REGISTRADO",
                resource_type="CONSENTIMENTO",
                resource_id=str(consent.id),
                user_id=principal.user_id,
                role=principal.role,
                details={
                    "finalidade": purpose.value,
                    "acao": action.value,
                    "versaoTermo": terms_version,
                },
            )
        )
        self._uow.commit()
        return consent


@dataclass(frozen=True, slots=True)
class ConsentOverview:
    history: list[Consent]
    current: dict[ConsentPurpose, Consent]


class ListConsents:
    def __init__(self, consents: ConsentRepository) -> None:
        self._consents = consents

    def execute(self, principal: Principal) -> ConsentOverview:
        _only_customer(principal)
        history = self._consents.history(principal.user_id)
        return ConsentOverview(history, Consent.current_by_purpose(history))
