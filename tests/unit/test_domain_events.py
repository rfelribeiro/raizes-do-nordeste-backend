import json
from dataclasses import FrozenInstanceError, dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import pytest

from raizes.domain.shared.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class OrderCreated(DomainEvent):
    store_id: int = 0

    def payload(self) -> dict[str, Any]:
        return {"store_id": self.store_id}


@dataclass(frozen=True, kw_only=True)
class FixedName(DomainEvent):
    event_type = "stable_name"


def _event() -> OrderCreated:
    return OrderCreated(aggregate_type="order", aggregate_id="42", store_id=7)


def test_event_type_derived_from_class_name() -> None:
    assert OrderCreated.event_type == "order_created"
    assert _event().event_type == "order_created"


def test_event_type_can_be_pinned_in_subclass() -> None:
    assert FixedName.event_type == "stable_name"


def test_default_metadata() -> None:
    event = _event()
    assert isinstance(event.event_id, UUID)
    assert event.event_id.version == 4
    assert event.schema_version == 1
    assert event.occurred_at.utcoffset() == timedelta(0)


def test_payload_is_json_serializable() -> None:
    assert json.loads(json.dumps(_event().payload())) == {"store_id": 7}


def test_event_is_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        _event().aggregate_id = "other"  # type: ignore[misc]


def test_naive_occurred_at_is_rejected() -> None:
    with pytest.raises(ValueError, match="fuso"):
        OrderCreated(aggregate_type="order", aggregate_id="1", occurred_at=datetime(2026, 1, 1))


def test_occurred_at_with_other_timezone_is_converted_to_utc() -> None:
    recife = timezone(timedelta(hours=-3))
    event = OrderCreated(
        aggregate_type="order",
        aggregate_id="1",
        occurred_at=datetime(2026, 1, 1, 9, 0, tzinfo=recife),
    )
    assert event.occurred_at == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    assert event.occurred_at.utcoffset() == timedelta(0)


def test_invalid_schema_version() -> None:
    with pytest.raises(ValueError, match="schema_version"):
        OrderCreated(aggregate_type="order", aggregate_id="1", schema_version=0)
