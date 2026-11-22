"""UC-11 Consultar Auditoria: ADMIN vê a rede toda; GERENTE só a sua unidade."""

from raizes.application.errors import PermissionDeniedError
from raizes.application.ports.audit import AuditFilter, AuditReader, AuditRecordView
from raizes.application.principal import Principal
from raizes.domain.shared.enums import Role


class QueryAudit:
    def __init__(self, reader: AuditReader) -> None:
        self._reader = reader

    def execute(
        self,
        principal: Principal,
        *,
        action: str | None,
        resource_type: str | None,
        page: int,
        limit: int,
    ) -> tuple[list[AuditRecordView], int]:
        if principal.role is Role.ADMIN:
            unit_id = None
        elif principal.role is Role.GERENTE and principal.unit_id is not None:
            unit_id = principal.unit_id
        else:
            raise PermissionDeniedError("Só GERENTE e ADMIN consultam a auditoria.")
        return self._reader.search(
            AuditFilter(action=action, resource_type=resource_type, unit_id=unit_id), page, limit
        )
