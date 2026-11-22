"""Rotas de pedidos: criar, listar, obter e atualizar status (UC-04, RF-08, UC-06)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from raizes.api.composition.orders import (
    get_create_order,
    get_get_order,
    get_list_orders,
    get_update_order_status,
)
from raizes.api.pagination import Page, PageQuery
from raizes.api.schemas.orders import CreateOrderRequest, OrderOut, UpdateStatusRequest
from raizes.api.security import get_principal, require_roles
from raizes.api.v1.docs import (
    E401,
    E403,
    E404,
    E409_ESTOQUE,
    E409_TRANSICAO,
    E422,
    erros,
)
from raizes.application.orders.create_order import CreateOrder, CreateOrderCommand, OrderItemInput
from raizes.application.orders.queries import GetOrder, ListOrders
from raizes.application.orders.update_status import UpdateOrderStatus
from raizes.application.principal import Principal
from raizes.domain.shared.enums import OrderChannel, OrderStatus, Role

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])

_CREATORS = (Role.CLIENTE, Role.ATENDENTE, Role.GERENTE)
_STATUS_ACTORS = (Role.COZINHA, Role.ATENDENTE, Role.GERENTE)


@router.post(
    "",
    status_code=201,
    summary="Cria um pedido e reserva o estoque",
    description=(
        "CLIENTE usa APP, WEB ou PICKUP; ATENDENTE e GERENTE (da unidade) usam BALCAO ou TOTEM. "
        "O pedido nasce em AGUARDANDO_PAGAMENTO e expira em 15 minutos."
    ),
    responses=erros(E401, E403, E404, E409_ESTOQUE, E422),
)
def create_order(
    body: CreateOrderRequest,
    response: Response,
    principal: Annotated[Principal, Depends(require_roles(*_CREATORS))],
    use_case: Annotated[CreateOrder, Depends(get_create_order)],
) -> OrderOut:
    order = use_case.execute(
        principal,
        CreateOrderCommand(
            unit_id=body.unit_id,
            channel=body.channel,
            customer_id=body.customer_id,
            items=[OrderItemInput(i.product_id, i.quantity) for i in body.items],
        ),
    )
    response.headers["Location"] = f"/api/v1/pedidos/{order.id}"
    return OrderOut.from_domain(order)


@router.get(
    "",
    summary="Lista pedidos conforme o escopo do perfil",
    description=(
        "CLIENTE vê só os seus; colaborador, só os da sua unidade; ADMIN, todos. "
        "Filtros: `canalPedido`, `status`, `unidadeId`."
    ),
    responses=erros(E401, E403, E422),
)
def list_orders(
    principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[ListOrders, Depends(get_list_orders)],
    page: PageQuery,
    channel: Annotated[OrderChannel | None, Query(alias="canalPedido")] = None,
    status: Annotated[OrderStatus | None, Query()] = None,
    unit_id: Annotated[UUID | None, Query(alias="unidadeId")] = None,
) -> Page[OrderOut]:
    orders, total = use_case.execute(
        principal,
        channel=channel,
        status=status,
        unit_id=unit_id,
        page=page.page,
        limit=page.limit,
    )
    return Page[OrderOut](
        items=[OrderOut.from_domain(o) for o in orders],
        page=page.page,
        limit=page.limit,
        total=total,
    )


@router.get(
    "/{order_id}",
    summary="Consulta um pedido com seus itens",
    responses=erros(E401, E403, E404),
)
def get_order(
    order_id: UUID,
    principal: Annotated[Principal, Depends(get_principal)],
    use_case: Annotated[GetOrder, Depends(get_get_order)],
) -> OrderOut:
    return OrderOut.from_domain(use_case.execute(principal, order_id))


@router.patch(
    "/{order_id}/status",
    summary="Atualiza o status do pedido (EM_PREPARO, PRONTO ou ENTREGUE)",
    description="O perfil é verificado antes da máquina de estados (403 antes de 409).",
    responses=erros(E401, E403, E404, E409_TRANSICAO, E422),
)
def update_status(
    order_id: UUID,
    body: UpdateStatusRequest,
    principal: Annotated[Principal, Depends(require_roles(*_STATUS_ACTORS))],
    use_case: Annotated[UpdateOrderStatus, Depends(get_update_order_status)],
) -> OrderOut:
    order = use_case.execute(principal, order_id, body.status, body.reason)
    return OrderOut.from_domain(order)
