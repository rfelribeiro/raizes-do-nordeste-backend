from datetime import UTC, datetime, timedelta
from uuid import uuid4

from raizes.domain.consent.consent import Consent
from raizes.domain.shared.enums import ConsentAction, ConsentPurpose

USER = uuid4()
T0 = datetime(2026, 11, 1, tzinfo=UTC)


def test_no_history_is_not_active() -> None:
    assert not Consent.is_active([], ConsentPurpose.FIDELIDADE)
    assert Consent.current([], ConsentPurpose.FIDELIDADE) is None


def test_latest_record_wins_per_purpose() -> None:
    history = [
        Consent.grant(USER, ConsentPurpose.FIDELIDADE, "v1", T0),
        Consent.grant(USER, ConsentPurpose.MARKETING, "v1", T0 + timedelta(hours=1)),
        Consent.revoke(USER, ConsentPurpose.FIDELIDADE, "v1", T0 + timedelta(hours=2)),
    ]
    assert not Consent.is_active(history, ConsentPurpose.FIDELIDADE)
    assert Consent.is_active(history, ConsentPurpose.MARKETING)
    assert not Consent.is_active(history, ConsentPurpose.DATA_NASCIMENTO)
    latest = Consent.current_by_purpose(history)
    assert latest[ConsentPurpose.FIDELIDADE].action is ConsentAction.REVOGADO
    assert set(latest) == {ConsentPurpose.FIDELIDADE, ConsentPurpose.MARKETING}


def test_regrant_after_revoke_is_active() -> None:
    history = [
        Consent.grant(USER, ConsentPurpose.FIDELIDADE, "v1", T0),
        Consent.revoke(USER, ConsentPurpose.FIDELIDADE, "v1", T0 + timedelta(hours=1)),
        Consent.grant(USER, ConsentPurpose.FIDELIDADE, "v2", T0 + timedelta(hours=2)),
    ]
    assert Consent.is_active(reversed(history), ConsentPurpose.FIDELIDADE)
    assert Consent.current(history, ConsentPurpose.FIDELIDADE).terms_version == "v2"  # type: ignore[union-attr]


def test_record_has_legal_basis_and_version() -> None:
    consent = Consent.grant(USER, ConsentPurpose.MARKETING, "2026-01")
    assert consent.legal_basis
    assert consent.terms_version == "2026-01"
    assert consent.recorded_at.tzinfo is not None
