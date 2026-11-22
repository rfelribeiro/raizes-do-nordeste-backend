"""Políticas do pedido: quem pode pedir cada transição (RN-04) e perfil x canal (RN-14)."""

from dataclasses import dataclass
from uuid import UUID

from raizes.domain.shared.enums import OrderChannel, OrderStatus, Role
from raizes.domain.shared.errors import DomainError

_S = OrderStatus

# RN-04: status de destino que cada perfil pode solicitar. PAGO nunca é manual. A validade da
# transição (atual -> alvo) é só da máquina de estados (`Order.advance_status`, 409).
_ROLE_TARGETS: dict[Role, frozenset[OrderStatus]] = {
    Role.COZINHA: frozenset({_S.EM_PREPARO, _S.PRONTO}),
    Role.ATENDENTE: frozenset({_S.ENTREGUE, _S.CANCELADO}),
    Role.GERENTE: frozenset({_S.EM_PREPARO, _S.PRONTO, _S.ENTREGUE, _S.CANCELADO}),
    Role.CLIENTE: frozenset({_S.CANCELADO}),
    Role.ADMIN: frozenset(),
}
_STAFF = frozenset({Role.COZINHA, Role.ATENDENTE, Role.GERENTE})


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    reason: str = ""

    def __bool__(self) -> bool:
        return self.allowed


class TransitionPolicy:
    """Decide se o perfil pode pedir a transição. A aplicação converte a negativa em 403.

    Roda ANTES da máquina de estados (UC-06): primeiro quem pode pedir o status alvo (403),
    depois se a transição é válida (409). `current` fica na assinatura por compatibilidade.
    """

    @staticmethod
    def evaluate(
        *,
        role: Role,
        current: OrderStatus,
        target: OrderStatus,
        user_unit_id: UUID | None,
        order_unit_id: UUID,
        is_owner: bool = False,
    ) -> PolicyDecision:
        if role in _STAFF and (user_unit_id is None or user_unit_id != order_unit_id):
            return PolicyDecision(False, "colaborador só atua na própria unidade")
        if role is Role.CLIENTE and not is_owner:
            return PolicyDecision(False, "cliente só atua no próprio pedido")
        if target not in _ROLE_TARGETS.get(role, frozenset()):
            return PolicyDecision(False, "perfil não pode solicitar esta transição")
        return PolicyDecision(True)


_CHANNELS_BY_ROLE: dict[Role, frozenset[OrderChannel]] = {
    Role.CLIENTE: frozenset({OrderChannel.APP, OrderChannel.WEB, OrderChannel.PICKUP}),
    Role.ATENDENTE: frozenset({OrderChannel.BALCAO, OrderChannel.TOTEM}),
    Role.GERENTE: frozenset({OrderChannel.BALCAO, OrderChannel.TOTEM}),
}


class ChannelPolicy:
    """RN-14: perfil x canal. COZINHA e ADMIN não criam pedido (a aplicação responde 403)."""

    @staticmethod
    def can_create_orders(role: Role) -> bool:
        return role in _CHANNELS_BY_ROLE

    @staticmethod
    def allowed_channels(role: Role) -> frozenset[OrderChannel]:
        return _CHANNELS_BY_ROLE.get(role, frozenset())

    @classmethod
    def validate(cls, role: Role, channel: OrderChannel) -> None:
        """Levanta `VALIDACAO_FALHOU` (422) se o canal for incompatível com o perfil."""
        if channel not in cls.allowed_channels(role):
            raise DomainError(
                "Canal incompatível com o perfil.",
                codigo="VALIDACAO_FALHOU",
                detalhes=[
                    {
                        "field": "canalPedido",
                        "issue": f"o perfil {role.value} não pode criar pedido no canal "
                        f"{channel.value}",
                    }
                ],
            )
