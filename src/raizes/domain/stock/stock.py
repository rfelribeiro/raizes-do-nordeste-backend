"""Agregado `Stock` (Estoque) e seu razão `StockMovement` (RN-05, RN-06)."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from raizes.domain.shared.enums import StockMovementType
from raizes.domain.shared.errors import BusinessRuleViolationError, DomainError


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class StockMovement:
    """Movimento append-only; a quantidade é sempre positiva e o sinal vem do tipo."""

    unit_id: UUID
    product_id: UUID
    type: StockMovementType
    quantity: int
    order_id: UUID | None = None
    user_id: UUID | None = None
    reason: str | None = None
    occurred_at: datetime = field(default_factory=_now)
    id: UUID = field(default_factory=uuid4)


def _positive(quantity: int) -> None:
    if quantity <= 0:
        raise DomainError(
            "Quantidade deve ser maior que zero.",
            codigo="VALIDACAO_FALHOU",
            detalhes=[{"field": "quantidade", "issue": "deve ser maior que zero"}],
        )


@dataclass(slots=True)
class Stock:
    unit_id: UUID
    product_id: UUID
    available: int = 0
    reserved: int = 0

    def __post_init__(self) -> None:
        if self.available < 0 or self.reserved < 0:
            raise ValueError("saldos de estoque não podem ser negativos")

    def _movement(
        self,
        type_: StockMovementType,
        quantity: int,
        order_id: UUID | None,
        user_id: UUID | None,
        reason: str | None,
    ) -> StockMovement:
        return StockMovement(
            unit_id=self.unit_id,
            product_id=self.product_id,
            type=type_,
            quantity=quantity,
            order_id=order_id,
            user_id=user_id,
            reason=reason,
        )

    def _insufficient(self) -> BusinessRuleViolationError:
        return BusinessRuleViolationError(
            "Estoque insuficiente.",
            codigo="ESTOQUE_INSUFICIENTE",
            detalhes=[
                {
                    "field": "produtoId",
                    "issue": f"produto {self.product_id}: disponível {self.available}",
                }
            ],
        )

    def reserve(self, quantity: int, order_id: UUID, user_id: UUID | None = None) -> StockMovement:
        """Disponível -> reservado. Saldo insuficiente: 409 ESTOQUE_INSUFICIENTE (RN-05)."""
        _positive(quantity)
        if quantity > self.available:
            raise self._insufficient()
        self.available -= quantity
        self.reserved += quantity
        return self._movement(StockMovementType.RESERVA, quantity, order_id, user_id, None)

    def release(self, quantity: int, order_id: UUID, user_id: UUID | None = None) -> StockMovement:
        """Reservado -> disponível (cancelamento, expiração; RN-06)."""
        _positive(quantity)
        if quantity > self.reserved:
            raise self._reserved_exceeded()
        self.reserved -= quantity
        self.available += quantity
        return self._movement(StockMovementType.LIBERACAO, quantity, order_id, user_id, None)

    def write_off(
        self, quantity: int, order_id: UUID, user_id: UUID | None = None
    ) -> StockMovement:
        """Baixa: a reserva sai do estoque no pagamento aprovado (RN-06)."""
        _positive(quantity)
        if quantity > self.reserved:
            raise self._reserved_exceeded()
        self.reserved -= quantity
        return self._movement(StockMovementType.BAIXA, quantity, order_id, user_id, None)

    def _reserved_exceeded(self) -> BusinessRuleViolationError:
        return BusinessRuleViolationError(
            "Quantidade maior que a reservada.",
            codigo="RESERVA_INSUFICIENTE",
            detalhes=[
                {
                    "field": "produtoId",
                    "issue": f"produto {self.product_id}: reservado {self.reserved}",
                }
            ],
        )

    def register_entry(
        self, quantity: int, user_id: UUID | None = None, reason: str | None = None
    ) -> StockMovement:
        """Entrada de mercadoria (UC-08)."""
        _positive(quantity)
        self.available += quantity
        return self._movement(StockMovementType.ENTRADA, quantity, None, user_id, reason)

    def adjust(
        self,
        quantity: int,
        *,
        positive: bool,
        reason: str,
        user_id: UUID | None = None,
        order_id: UUID | None = None,
    ) -> StockMovement:
        """Ajuste manual ou devolução por cancelamento; o motivo é obrigatório."""
        _positive(quantity)
        if not reason or not reason.strip():
            raise DomainError(
                "O motivo do ajuste é obrigatório.",
                codigo="VALIDACAO_FALHOU",
                detalhes=[{"field": "motivo", "issue": "obrigatório"}],
            )
        if positive:
            self.available += quantity
            type_ = StockMovementType.AJUSTE_POSITIVO
        else:
            if quantity > self.available:
                raise self._insufficient()
            self.available -= quantity
            type_ = StockMovementType.AJUSTE_NEGATIVO
        return self._movement(type_, quantity, order_id, user_id, reason)
