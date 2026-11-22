"""Valores monetários: `Decimal` com 2 casas (BRL), arredondamento bancário (ROUND_HALF_EVEN)."""

from decimal import ROUND_HALF_EVEN, Decimal

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def to_money(value: Decimal | int | str) -> Decimal:
    """Converte para `Decimal` com 2 casas. Nunca aceita `float` (imprecisão binária)."""
    if isinstance(value, float):
        raise TypeError("use Decimal, int ou str para valores monetários")
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_EVEN)
