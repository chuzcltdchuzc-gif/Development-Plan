"""EvidenceRecord aggregate — domain invariants (B5 Slice B5.2, docs/adr/
ADR-026-evidence-domain-model.md).

Pure domain-layer tests, no repository, no HTTP, no database — the aggregate
enforces its invariants regardless of persistence, exactly as
tests/test_b3_registry.py's own Parcel-level tests do for Parcel.
"""
from __future__ import annotations

import pytest

from app.contexts.evidence.domain.evidence_record import (
    STATUS_HASHED,
    STATUS_RECEIVED,
    STATUS_SEALED,
    EvidenceLifecycleError,
    EvidenceRecord,
    EvidenceSealedError,
)


def _new_record(**overrides: object) -> EvidenceRecord:
    defaults: dict[object, object] = dict(
        tenant_id="ten_1",
        parcel_id="par_1",
        uploaded_by="usr_1",
        filename="survey.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        storage_key="evidence/ten_1/par_1/survey.pdf",
        basis="submitted by registrant as supporting survey documentation",
        evidence_type="SURVEY_PLAN",
    )
    defaults.update(overrides)
    return EvidenceRecord.new(**defaults)  # type: ignore[arg-type]


def test_new_creates_received_status_with_all_fields() -> None:
    record = _new_record()

    assert record.status == STATUS_RECEIVED
    assert record.evidence_id
    assert record.sha256 is None
    assert record.worm_grade is None
    assert record.legal_hold is False
    assert record.filename == "survey.pdf"


def test_new_rejects_unknown_evidence_type() -> None:
    with pytest.raises(ValueError, match="unknown evidence_type"):
        _new_record(evidence_type="NOT_A_REAL_TYPE")


def test_new_rejects_non_positive_size_bytes() -> None:
    with pytest.raises(ValueError, match="size_bytes must be positive"):
        _new_record(size_bytes=0)


def test_new_rejects_empty_storage_key() -> None:
    with pytest.raises(ValueError, match="storage_key is required"):
        _new_record(storage_key="")


def test_mark_hashed_transitions_to_hashed_and_sets_sha256() -> None:
    record = _new_record()

    record.mark_hashed(sha256="a" * 64)

    assert record.status == STATUS_HASHED
    assert record.sha256 == "a" * 64


def test_mark_hashed_twice_raises_lifecycle_error() -> None:
    record = _new_record()
    record.mark_hashed(sha256="a" * 64)

    with pytest.raises(EvidenceLifecycleError):
        record.mark_hashed(sha256="b" * 64)


def test_mark_hashed_requires_a_sha256() -> None:
    record = _new_record()

    with pytest.raises(ValueError, match="sha256 is required"):
        record.mark_hashed(sha256="")


def test_seal_before_hashed_raises_lifecycle_error() -> None:
    record = _new_record()

    with pytest.raises(EvidenceLifecycleError):
        record.seal(worm_grade="governance")


def test_seal_transitions_to_sealed_and_sets_worm_grade() -> None:
    record = _new_record()
    record.mark_hashed(sha256="a" * 64)

    record.seal(worm_grade="governance")

    assert record.status == STATUS_SEALED
    assert record.worm_grade == "governance"
    assert record.is_sealed() is True


def test_seal_rejects_unknown_worm_grade() -> None:
    record = _new_record()
    record.mark_hashed(sha256="a" * 64)

    with pytest.raises(ValueError, match="unknown worm_grade"):
        record.seal(worm_grade="not_a_real_grade")


def test_mark_hashed_after_sealed_raises_sealed_error() -> None:
    record = _new_record()
    record.mark_hashed(sha256="a" * 64)
    record.seal(worm_grade="governance")

    with pytest.raises(EvidenceSealedError):
        record.mark_hashed(sha256="c" * 64)


def test_seal_after_sealed_raises_sealed_error() -> None:
    record = _new_record()
    record.mark_hashed(sha256="a" * 64)
    record.seal(worm_grade="governance")

    with pytest.raises(EvidenceSealedError):
        record.seal(worm_grade="compliance")


def test_legal_hold_can_be_applied_before_sealing() -> None:
    record = _new_record()

    record.apply_legal_hold(reason="pending dispute review", applied_by="usr_governance")

    assert record.legal_hold is True
    assert record.legal_hold_reason == "pending dispute review"
    assert record.legal_hold_by == "usr_governance"
    assert record.status == STATUS_RECEIVED  # legal hold does not touch the lifecycle status


def test_legal_hold_can_be_applied_after_sealing() -> None:
    """ADR-026 invariant #4's one named exception: legal_hold/
    legal_hold_reason/legal_hold_by remain mutable even once SEALED."""
    record = _new_record()
    record.mark_hashed(sha256="a" * 64)
    record.seal(worm_grade="governance")

    record.apply_legal_hold(reason="pending dispute review", applied_by="usr_governance")

    assert record.legal_hold is True
    assert record.status == STATUS_SEALED  # sealing is unaffected by the hold


def test_apply_legal_hold_requires_a_reason() -> None:
    record = _new_record()

    with pytest.raises(ValueError, match="legal hold requires a reason"):
        record.apply_legal_hold(reason="", applied_by="usr_governance")


def test_release_legal_hold_clears_all_fields() -> None:
    record = _new_record()
    record.apply_legal_hold(reason="pending dispute review", applied_by="usr_governance")

    record.release_legal_hold()

    assert record.legal_hold is False
    assert record.legal_hold_reason is None
    assert record.legal_hold_by is None


def test_filename_mime_type_size_bytes_evidence_type_have_no_setters() -> None:
    """ADR-026 invariant #2/structural immutability: these fields exist
    from creation and no method on this class ever changes them — the
    invariant holds because no code path can, not because of a runtime
    guard. This test documents the invariant by asserting no such method
    exists, so an accidental future addition is caught by a failing test,
    not discovered as a silent behavior change."""
    disallowed_methods = {
        "set_filename",
        "set_mime_type",
        "set_size_bytes",
        "set_evidence_type",
        "update_details",
    }
    actual_methods = {name for name in dir(EvidenceRecord) if not name.startswith("_")}
    assert disallowed_methods.isdisjoint(actual_methods)
