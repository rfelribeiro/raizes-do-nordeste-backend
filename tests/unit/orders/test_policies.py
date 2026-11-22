from uuid import uuid4

import pytest

from raizes.domain.orders.policies import ChannelPolicy, TransitionPolicy
from raizes.domain.shared.enums import OrderChannel, OrderStatus, Role
from raizes.domain.shared.errors import DomainError

S = OrderStatus
R = Role

# Matriz RN-04: (perfil, de, para) permitidos, na própria unidade / como dono.
ALLOWED = {
    (R.COZINHA, S.PAGO, S.EM_PREPARO),
    (R.COZINHA, S.EM_PREPARO, S.PRONTO),
    (R.ATENDENTE, S.PRONTO, S.ENTREGUE),
    (R.ATENDENTE, S.AGUARDANDO_PAGAMENTO, S.CANCELADO),
    (R.ATENDENTE, S.PAGO, S.CANCELADO),
    (R.GERENTE, S.PAGO, S.EM_PREPARO),
    (R.GERENTE, S.EM_PREPARO, S.PRONTO),
    (R.GERENTE, S.PRONTO, S.ENTREGUE),
    (R.GERENTE, S.AGUARDANDO_PAGAMENTO, S.CANCELADO),
    (R.GERENTE, S.PAGO, S.CANCELADO),
    (R.CLIENTE, S.AGUARDANDO_PAGAMENTO, S.CANCELADO),
}


@pytest.mark.parametrize("role", list(Role))
@pytest.mark.parametrize("current", list(OrderStatus))
@pytest.mark.parametrize("target", list(OrderStatus))
def test_role_status_matrix(role: Role, current: OrderStatus, target: OrderStatus) -> None:
    unit = uuid4()
    decision = TransitionPolicy.evaluate(
        role=role,
        current=current,
        target=target,
        user_unit_id=unit if role not in (R.CLIENTE, R.ADMIN) else None,
        order_unit_id=unit,
        is_owner=True,
    )
    assert decision.allowed == ((role, current, target) in ALLOWED)


@pytest.mark.parametrize("role", [R.COZINHA, R.ATENDENTE, R.GERENTE])
def test_staff_of_other_unit_is_denied_even_for_allowed_transition(role: Role) -> None:
    pair = next((c, t) for r, c, t in ALLOWED if r is role)
    decision = TransitionPolicy.evaluate(
        role=role,
        current=pair[0],
        target=pair[1],
        user_unit_id=uuid4(),
        order_unit_id=uuid4(),
    )
    assert not decision.allowed


def test_client_must_own_order() -> None:
    kwargs = dict(
        role=R.CLIENTE,
        current=S.AGUARDANDO_PAGAMENTO,
        target=S.CANCELADO,
        user_unit_id=None,
        order_unit_id=uuid4(),
    )
    assert TransitionPolicy.evaluate(**kwargs, is_owner=True)  # type: ignore[arg-type]
    assert not TransitionPolicy.evaluate(**kwargs, is_owner=False)  # type: ignore[arg-type]


@pytest.mark.parametrize("role", list(Role))
def test_paid_is_never_manual(role: Role) -> None:
    unit = uuid4()
    assert not TransitionPolicy.evaluate(
        role=role,
        current=S.AGUARDANDO_PAGAMENTO,
        target=S.PAGO,
        user_unit_id=unit,
        order_unit_id=unit,
        is_owner=True,
    ).allowed


CHANNELS = {
    R.CLIENTE: {OrderChannel.APP, OrderChannel.WEB, OrderChannel.PICKUP},
    R.ATENDENTE: {OrderChannel.BALCAO, OrderChannel.TOTEM},
    R.GERENTE: {OrderChannel.BALCAO, OrderChannel.TOTEM},
    R.COZINHA: set(),
    R.ADMIN: set(),
}


@pytest.mark.parametrize("role", list(Role))
@pytest.mark.parametrize("channel", list(OrderChannel))
def test_role_channel_matrix(role: Role, channel: OrderChannel) -> None:
    assert ChannelPolicy.can_create_orders(role) == bool(CHANNELS[role])
    if channel in CHANNELS[role]:
        ChannelPolicy.validate(role, channel)
    else:
        with pytest.raises(DomainError) as exc:
            ChannelPolicy.validate(role, channel)
        assert exc.value.codigo == "VALIDACAO_FALHOU"
        assert exc.value.detalhes[0]["field"] == "canalPedido"
        assert exc.value.detalhes[0]["issue"]
