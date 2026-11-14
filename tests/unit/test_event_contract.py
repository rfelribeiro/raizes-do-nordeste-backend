"""Valida o envelope serializado da outbox contra o JSON Schema do contrato de dados."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from raizes.domain.shared.events import DomainEvent

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts" / "events"
SCHEMA_PATH = CONTRACTS_DIR / "outbox_evento_envelope.schema.json"


@dataclass(frozen=True, kw_only=True)
class OrderCreated(DomainEvent):
    event_type = "pedido_criado"
    unidade_id: int = 0

    def payload(self) -> dict[str, Any]:
        return {"unidade_id": self.unidade_id}


def _to_outbox_envelope(event: DomainEvent) -> dict[str, Any]:
    """Reproduz o que a outbox grava/expõe: campos do evento + campos atribuídos pelo banco."""
    return {
        "id_evento": str(event.event_id),
        "tipo_evento": event.event_type,
        "versao_schema": event.schema_version,
        "tipo_agregado": event.aggregate_type,
        "id_agregado": event.aggregate_id,
        "payload": event.payload(),
        "ocorrido_em": event.occurred_at.isoformat(),
        "registrado_em": (event.occurred_at + timedelta(milliseconds=5)).isoformat(),
        "id_sequencial": 1,
    }


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _event() -> OrderCreated:
    return OrderCreated(
        aggregate_type="pedido",
        aggregate_id="42",
        unidade_id=7,
        occurred_at=datetime(2026, 11, 2, 12, 0, tzinfo=UTC),
    )


def test_serialized_event_matches_contract(validator: Draft202012Validator) -> None:
    validator.validate(_to_outbox_envelope(_event()))


def test_missing_field_violates_contract(validator: Draft202012Validator) -> None:
    envelope = _to_outbox_envelope(_event())
    del envelope["versao_schema"]
    with pytest.raises(ValidationError):
        validator.validate(envelope)


def test_unknown_field_violates_contract(validator: Draft202012Validator) -> None:
    envelope = {**_to_outbox_envelope(_event()), "campo_extra": 1}
    with pytest.raises(ValidationError):
        validator.validate(envelope)


@pytest.mark.parametrize("bad_type", ["PedidoCriado", "pedido.criado", "Pedido_criado", ""])
def test_event_type_must_be_snake_case(validator: Draft202012Validator, bad_type: str) -> None:
    envelope = {**_to_outbox_envelope(_event()), "tipo_evento": bad_type}
    with pytest.raises(ValidationError):
        validator.validate(envelope)


def test_payload_must_be_object(validator: Draft202012Validator) -> None:
    envelope = {**_to_outbox_envelope(_event()), "payload": [1, 2]}
    with pytest.raises(ValidationError):
        validator.validate(envelope)
