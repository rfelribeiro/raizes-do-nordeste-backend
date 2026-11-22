"""Schemas de pedidos (RF-07, RF-08, RF-09)."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from raizes.api.schemas.common import ApiModel, Money
from raizes.domain.orders.order import Order
from raizes.domain.shared.enums import OrderChannel, OrderStatus


class OrderItemIn(ApiModel):
    product_id: UUID = Field(alias="produtoId")
    quantity: int = Field(alias="quantidade", ge=1, le=999, examples=[2])


class CreateOrderRequest(ApiModel):
    unit_id: UUID = Field(alias="unidadeId")
    channel: OrderChannel = Field(
        alias="canalPedido", description="Obrigatório; imutável depois (RN-11)."
    )
    customer_id: UUID | None = Field(
        default=None,
        alias="clienteId",
        description="Só ATENDENTE/GERENTE; o CLIENTE sempre cria para si.",
    )
    items: list[OrderItemIn] = Field(alias="itens", min_length=1)

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "examples": [
                {
                    "unidadeId": "00000000-0000-4000-8000-000000000101",
                    "canalPedido": "APP",
                    "itens": [
                        {"produtoId": "00000000-0000-4000-8000-000000000301", "quantidade": 2}
                    ],
                }
            ]
        },
    }


class OrderItemOut(ApiModel):
    product_id: UUID = Field(alias="produtoId")
    quantity: int = Field(alias="quantidade")
    unit_price: Money = Field(alias="precoUnitario", examples=["12.00"])
    line_total: Money = Field(alias="valorTotalItem", examples=["24.00"])


class OrderOut(ApiModel):
    id: UUID
    order_number: int | None = Field(alias="numeroPedido")
    unit_id: UUID = Field(alias="unidadeId")
    customer_id: UUID | None = Field(alias="clienteId")
    channel: OrderChannel = Field(alias="canalPedido")
    status: OrderStatus
    items: list[OrderItemOut] = Field(alias="itens")
    items_value: Money = Field(alias="valorItens", examples=["24.00"])
    discount_value: Money = Field(alias="valorDesconto", examples=["0.00"])
    total_value: Money = Field(alias="valorTotal", examples=["24.00"])
    expires_at: datetime = Field(alias="expiraEm")
    created_at: datetime = Field(alias="criadoEm")

    @classmethod
    def from_domain(cls, order: Order) -> OrderOut:
        return cls(
            id=order.id,
            order_number=order.order_number,
            unit_id=order.unit_id,
            customer_id=order.customer_id,
            channel=order.channel,
            status=order.status,
            items=[
                OrderItemOut(
                    product_id=i.product_id,
                    quantity=i.quantity,
                    unit_price=i.unit_price,
                    line_total=i.total,
                )
                for i in order.items
            ],
            items_value=order.items_value,
            discount_value=order.discount_value,
            total_value=order.total_value,
            expires_at=order.expires_at,
            created_at=order.created_at,
        )


class UpdateStatusRequest(ApiModel):
    status: OrderStatus = Field(description="Aceitos: EM_PREPARO, PRONTO e ENTREGUE.")
    reason: str | None = Field(default=None, alias="motivo", max_length=255)

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {"examples": [{"status": "EM_PREPARO"}]},
    }
