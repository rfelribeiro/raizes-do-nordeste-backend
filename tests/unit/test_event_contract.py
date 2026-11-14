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
SCHEMA_PATH = CONTRACTS_DIR / "outbox_event_envelope.schema.json"


@dataclass(frozen=True, kw_only=True)
class OrderCreated(DomainEvent):
    store_id: int = 0

    def payload(self) -> dict[str, Any]:
        return {"store_id": self.store_id}


def _to_outbox_envelope(event: DomainEvent) -> dict[str, Any]:
    """Reproduz o que a outbox grava/expõe: campos do evento + campos atribuídos pelo banco."""
    return {
        "event_id": str(event.event_id),
        "event_type": event.event_type,
        "schema_version": event.schema_version,
        "aggregate_type": event.aggregate_type,
        "aggregate_id": event.aggregate_id,
        "payload": event.payload(),
        "occurred_at": event.occurred_at.isoformat(),
        "recorded_at": (event.occurred_at + timedelta(milliseconds=5)).isoformat(),
        "sequence_id": 1,
    }


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _event() -> OrderCreated:
    return OrderCreated(
        aggregate_type="order",
        aggregate_id="42",
        store_id=7,
        occurred_at=datetime(2026, 11, 2, 12, 0, tzinfo=UTC),
    )


def test_serialized_event_matches_contract(validator: Draft202012Validator) -> None:
    validator.validate(_to_outbox_envelope(_event()))


def test_missing_field_violates_contract(validator: Draft202012Validator) -> None:
    envelope = _to_outbox_envelope(_event())
    del envelope["schema_version"]
    with pytest.raises(ValidationError):
        validator.validate(envelope)


def test_unknown_field_violates_contract(validator: Draft202012Validator) -> None:
    envelope = {**_to_outbox_envelope(_event()), "extra_field": 1}
    with pytest.raises(ValidationError):
        validator.validate(envelope)


@pytest.mark.parametrize("bad_type", ["OrderCreated", "order.created", "Order_created", ""])
def test_event_type_must_be_snake_case(validator: Draft202012Validator, bad_type: str) -> None:
    envelope = {**_to_outbox_envelope(_event()), "event_type": bad_type}
    with pytest.raises(ValidationError):
        validator.validate(envelope)


def test_payload_must_be_object(validator: Draft202012Validator) -> None:
    envelope = {**_to_outbox_envelope(_event()), "payload": [1, 2]}
    with pytest.raises(ValidationError):
        validator.validate(envelope)
