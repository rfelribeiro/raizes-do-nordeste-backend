"""GET /auditoria (UC-11)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from raizes.api.composition.audit import get_query_audit
from raizes.api.pagination import Page, PageQuery
from raizes.api.schemas.audit import AuditOut
from raizes.api.security import require_roles
from raizes.api.v1.docs import E401, E403, E422, erros
from raizes.application.audit.query_audit import QueryAudit
from raizes.application.principal import Principal
from raizes.domain.shared.enums import Role

router = APIRouter(prefix="/auditoria", tags=["Auditoria"])


@router.get(
    "",
    summary="Consulta a trilha de auditoria, do mais recente ao mais antigo",
    description="ADMIN vê a rede inteira; GERENTE, só a sua unidade.",
    responses=erros(E401, E403, E422),
)
def query_audit(
    principal: Annotated[Principal, Depends(require_roles(Role.ADMIN, Role.GERENTE))],
    use_case: Annotated[QueryAudit, Depends(get_query_audit)],
    page: PageQuery,
    action: Annotated[str | None, Query(alias="acao", max_length=40)] = None,
    resource_type: Annotated[str | None, Query(alias="tipoRecurso", max_length=30)] = None,
) -> Page[AuditOut]:
    views, total = use_case.execute(
        principal,
        action=action,
        resource_type=resource_type,
        page=page.page,
        limit=page.limit,
    )
    return Page[AuditOut](
        items=[AuditOut.from_view(v) for v in views], page=page.page, limit=page.limit, total=total
    )
