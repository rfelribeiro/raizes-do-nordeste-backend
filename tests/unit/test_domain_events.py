import json
from dataclasses import FrozenInstanceError, dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import pytest

from raizes.domain.shared.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class PedidoCriado(DomainEvent):
    id_unidade: int = 0

    def payload(self) -> dict[str, Any]:
        return {"id_unidade": self.id_unidade}


@dataclass(frozen=True, kw_only=True)
class NomeFixo(DomainEvent):
    event_type = "nome_estavel"


def _evento() -> PedidoCriado:
    return PedidoCriado(aggregate_type="pedido", aggregate_id="42", id_unidade=7)


def test_event_type_derivado_do_nome_da_classe() -> None:
    assert PedidoCriado.event_type == "pedido_criado"
    assert _evento().event_type == "pedido_criado"


def test_event_type_pode_ser_fixado_na_subclasse() -> None:
    assert NomeFixo.event_type == "nome_estavel"


def test_metadados_padrao() -> None:
    evento = _evento()
    assert isinstance(evento.event_id, UUID)
    assert evento.event_id.version == 4
    assert evento.schema_version == 1
    assert evento.occurred_at.utcoffset() == timedelta(0)


def test_payload_serializavel_em_json() -> None:
    assert json.loads(json.dumps(_evento().payload())) == {"id_unidade": 7}


def test_evento_e_imutavel() -> None:
    with pytest.raises(FrozenInstanceError):
        _evento().aggregate_id = "outro"  # type: ignore[misc]


def test_occurred_at_naive_e_rejeitado() -> None:
    with pytest.raises(ValueError, match="fuso"):
        PedidoCriado(aggregate_type="pedido", aggregate_id="1", occurred_at=datetime(2026, 1, 1))


def test_occurred_at_com_outro_fuso_e_convertido_para_utc() -> None:
    recife = timezone(timedelta(hours=-3))
    evento = PedidoCriado(
        aggregate_type="pedido",
        aggregate_id="1",
        occurred_at=datetime(2026, 1, 1, 9, 0, tzinfo=recife),
    )
    assert evento.occurred_at == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    assert evento.occurred_at.utcoffset() == timedelta(0)


def test_schema_version_invalida() -> None:
    with pytest.raises(ValueError, match="schema_version"):
        PedidoCriado(aggregate_type="pedido", aggregate_id="1", schema_version=0)
