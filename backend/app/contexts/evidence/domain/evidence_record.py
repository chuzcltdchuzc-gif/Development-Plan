"""EvidenceRecord aggregate — the canonical, single authoritative
representation of one uploaded piece of evidence (B5 Slice B5.2, docs/adr/
ADR-026-evidence-domain-model.md).

`evidence_id` is immutable identity, set once at construction, matching
every other aggregate's `<name>_id` convention in this codebase
(app.contexts.registry.domain.parcel.Parcel, ParcelGeometry). `filename`/
`mime_type`/`size_bytes`/`evidence_type` are immutable from creation — no
method on this class ever changes them, so the invariant holds structurally
(no setter exists), the same discipline `parcel_id`'s own immutability
already relies on. `sha256` and `worm_grade` become immutable once set
(`mark_hashed`/`seal` each raise if called a second time), mirroring
`Parcel.allocate_parcel_number()`'s "reserve the field" guard.

Status moves one-way, `RECEIVED -> HASHED -> SEALED`, never backward, never
skipped — a `SEALED` record without a verified hash would defeat the
integrity guarantee this context exists to provide (ADR-026 invariant #3).
Once `SEALED`, no field may change except `legal_hold`/`legal_hold_reason`/
`legal_hold_by` (ADR-026 invariant #4) — `_ensure_not_sealed()` is the guard
every other mutator calls first, the identical shape
`Parcel._ensure_mutable()` already established for archived parcels.

This class does not compute hashes and does not call StoragePort — both are
later slices' concern (B5.3/B5.4). `mark_hashed`/`seal` accept an
already-computed `sha256`/`worm_grade` as parameters, exactly as
`Parcel.allocate_parcel_number()` accepts an already-allocated number rather
than allocating one itself (that's `ParcelNumberAllocator`'s job, a
different port).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

STATUS_RECEIVED = "RECEIVED"
STATUS_HASHED = "HASHED"
STATUS_SEALED = "SEALED"

# ADR-026 "Decision" — a starting, deliberately small set; extending it is
# an additive, non-breaking change (a new member), not a reason to revisit
# the ADR.
EVIDENCE_TYPES: frozenset[str] = frozenset(
    {"SURVEY_PLAN", "TITLE_DOCUMENT", "IDENTITY_DOCUMENT", "OTHER"}
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class EvidenceSealedError(Exception):
    """Raised when a mutation other than legal_hold/legal_hold_reason/
    legal_hold_by is attempted against a SEALED EvidenceRecord (ADR-026
    invariant #4)."""


class EvidenceLifecycleError(Exception):
    """Raised when a lifecycle transition is attempted out of order —
    sealing before hashing, hashing twice, or hashing an already-hashed
    record (ADR-026 invariant #3)."""


@dataclass
class EvidenceRecord:
    evidence_id: str
    tenant_id: str
    parcel_id: str
    uploaded_by: str
    filename: str
    mime_type: str
    size_bytes: int
    storage_key: str
    basis: str
    evidence_type: str
    status: str = STATUS_RECEIVED
    sha256: str | None = None
    worm_grade: str | None = None
    legal_hold: bool = False
    legal_hold_reason: str | None = None
    legal_hold_by: str | None = None
    audit_ref: str | None = None
    created_at: str = field(default_factory=_now_iso)

    @classmethod
    def new(
        cls,
        *,
        tenant_id: str,
        parcel_id: str,
        uploaded_by: str,
        filename: str,
        mime_type: str,
        size_bytes: int,
        storage_key: str,
        basis: str,
        evidence_type: str,
        audit_ref: str | None = None,
    ) -> EvidenceRecord:
        if evidence_type not in EVIDENCE_TYPES:
            raise ValueError(f"unknown evidence_type: {evidence_type!r}")
        if size_bytes <= 0:
            raise ValueError("size_bytes must be positive")
        if not storage_key:
            raise ValueError("storage_key is required — the storage write must precede this call")
        return cls(
            evidence_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            parcel_id=parcel_id,
            uploaded_by=uploaded_by,
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            storage_key=storage_key,
            basis=basis,
            evidence_type=evidence_type,
            audit_ref=audit_ref,
        )

    def is_sealed(self) -> bool:
        return self.status == STATUS_SEALED

    def _ensure_not_sealed(self) -> None:
        """Every mutator except the legal-hold pair must call this first —
        the one guard every future mutation inherits, so "sealed records
        cannot be modified, except legal hold" is enforced structurally,
        not re-implemented per method (ADR-026 invariant #4)."""
        if self.is_sealed():
            raise EvidenceSealedError("cannot modify a sealed evidence record")

    def mark_hashed(self, *, sha256: str) -> None:
        """RECEIVED -> HASHED. `sha256` must already be computed by the
        caller (B5.3) — this method does not hash anything itself."""
        self._ensure_not_sealed()
        if self.status != STATUS_RECEIVED:
            raise EvidenceLifecycleError(
                f"cannot mark hashed from status {self.status!r}; expected {STATUS_RECEIVED!r}"
            )
        if not sha256:
            raise ValueError("sha256 is required")
        self.sha256 = sha256
        self.status = STATUS_HASHED

    def seal(self, *, worm_grade: str) -> None:
        """HASHED -> SEALED. `worm_grade` must already be reported by the
        storage adapter the caller (B5.4) used — this method does not call
        StoragePort itself."""
        self._ensure_not_sealed()
        if self.status != STATUS_HASHED:
            raise EvidenceLifecycleError(
                f"cannot seal from status {self.status!r}; expected {STATUS_HASHED!r}"
            )
        if worm_grade not in ("governance", "compliance"):
            raise ValueError(f"unknown worm_grade: {worm_grade!r}")
        self.worm_grade = worm_grade
        self.status = STATUS_SEALED

    def apply_legal_hold(self, *, reason: str, applied_by: str) -> None:
        """Legal hold is orthogonal to `status` (ADR-026) — deliberately
        does NOT call `_ensure_not_sealed()`, since applying a hold to a
        SEALED record is exactly invariant #4's one named exception, and
        applying one before sealing is unrestricted (no invariant blocks
        it either). The actual enforcement of what a hold blocks
        (delete/archive/seal-release call sites) is Slice B5.6, per
        ADR-026 invariant #5 — this method only records the hold's state."""
        if not reason:
            raise ValueError("legal hold requires a reason")
        self.legal_hold = True
        self.legal_hold_reason = reason
        self.legal_hold_by = applied_by

    def release_legal_hold(self) -> None:
        self.legal_hold = False
        self.legal_hold_reason = None
        self.legal_hold_by = None
