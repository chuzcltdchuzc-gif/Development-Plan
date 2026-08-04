"""Ports the Evidence application layer depends on (B5). Concrete adapters
implement these; tests use in-memory fakes — the identical "ports before
adapters" discipline every prior context in this codebase follows
(app.contexts.registry.ports, docs/adr/ADR-002).

StoragePort — the provider-agnostic object-storage seam (B5 Slice B5.1,
docs/adr/ADR-024-delivery-platform-and-infrastructure-decisions.md D1, refined
by docs/adr/ADR-025-supabase-platform-baseline.md E3). No bounded context
calls a storage SDK directly (LV-000 v1.8, Article X §5) — Evidence is the
sole consumer of this port (docs/adr/ADR-007-audit-trail-evidence-model.md's
"route through this same pipeline rather than each building its own weaker
version").

This Protocol's shape is already decided by the two ADRs above; defining it
requires no new architectural decision (see docs/adr/
ADR-026-evidence-domain-model.md, "Relationship to Slice B5.1" — the same
port-before-aggregate sequencing docs/adr/
ADR-016-geometry-port-boundary-spatial-integration.md already established for
GeometryPort). No real adapter (Supabase Storage, Cloudflare R2) is
implemented against this Protocol yet: both require a new external
dependency (docs/ENGINEERING_RULES.md rule 5 — human approval, justification,
pinned version) and real credentials for live verification
(docs/ENGINEERING_RULES.md rule 7 — never mark complete without having
observed it pass against real infrastructure), neither of which this slice
can supply on its own. Only an in-memory fake exists today
(backend/tests/fakes/storage.py), for hermetic testing of whatever future
service consumes this port.

EvidenceRepository — the EvidenceRecord aggregate's persistence port (B5
Slice B5.2, docs/adr/ADR-026-evidence-domain-model.md "EvidenceRepository
port"). Deliberately narrow, mirroring
app.contexts.registry.ports.ParcelHistoryRepository's shape: no generic
update/delete method exists on this Protocol at all — only the specific,
guarded lifecycle transitions the aggregate itself exposes
(mark_hashed/seal/set_legal_hold), so "which mutations are possible" is
visible from the port's own shape, not only from the aggregate's methods.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol

from app.contexts.evidence.domain.evidence_record import EvidenceRecord

WormGrade = Literal["governance", "compliance"]


class StorageObjectNotFoundError(Exception):
    """Raised by `get`/`list_keys` operations against a key that was never
    written. Distinct from an empty result: a caller asking for a specific
    key that does not exist gets a clear signal, not a silently empty value
    that could be mistaken for "exists but is empty"."""


class StorageImmutabilityViolationError(Exception):
    """Raised by any `put`/`put_immutable` call against a key that has
    already been sealed via `put_immutable`. This is the mechanical
    enforcement of "sealed evidence cannot be altered"
    (docs/EXECUTION_PLAN.md Phase-3 gate text) — an adapter that could
    silently overwrite a sealed key would defeat the entire reason this
    port exists (docs/adr/ADR-007-audit-trail-evidence-model.md's founding
    motivation: prior "WORM" implementations were fake at the storage
    layer). Every StoragePort implementation, real or fake, must raise
    this rather than permit the write."""


class StoragePort(Protocol):
    """put / get / list_keys, plus put_immutable(retention_until) and
    worm_grade() — the exact shape docs/adr/ADR-024-...md D1 and
    docs/EXECUTION_PLAN.md §7.2 specify, in this codebase's own snake_case
    convention. `key` is an opaque, adapter-chosen identifier — callers
    never construct or parse it, so escalating the backing adapter
    (governance-grade to compliance-grade) never requires a caller-side
    code change (docs/adr/ADR-024-...md D1's replacement criteria,
    Article VII §3)."""

    async def put(
        self, key: str, data: bytes, *, content_type: str | None = None
    ) -> None:
        """Write (or overwrite) `key`. Raises StorageImmutabilityViolationError
        if `key` was previously sealed via put_immutable — ordinary put
        never overwrites sealed data, regardless of caller."""
        ...

    async def get(self, key: str) -> bytes:
        """Raises StorageObjectNotFoundError if `key` was never written."""
        ...

    async def list_keys(self, prefix: str) -> list[str]:
        """Returns every key starting with `prefix`, in a deterministic
        (sorted) order. Empty list if none match — this is a legitimate
        result, unlike `get` against a missing key."""
        ...

    async def put_immutable(
        self,
        key: str,
        data: bytes,
        *,
        retention_until: datetime,
        content_type: str | None = None,
    ) -> None:
        """Seals `key` under the adapter's own WORM/object-lock guarantee
        (Cloudflare R2 Bucket Locks, S3 Object Lock, etc., per the adapter
        actually wired). Raises StorageImmutabilityViolationError if `key`
        was already sealed — sealing is one-way and idempotent-refusing,
        never a silent re-seal with different content or a different
        retention_until."""
        ...

    def worm_grade(self) -> WormGrade:
        """The retention guarantee this adapter's backend actually
        provides — "governance" (revocable by a privileged administrator,
        e.g. Cloudflare R2 Bucket Locks) or "compliance" (irrevocable, e.g.
        S3 Object Lock compliance mode). Not a per-call value: one adapter
        instance has exactly one grade for its whole lifetime."""
        ...


class EvidenceRepository(Protocol):
    async def add(self, record: EvidenceRecord) -> EvidenceRecord: ...
    async def get(self, evidence_id: str) -> EvidenceRecord | None: ...
    async def list_for_parcel(self, parcel_id: str) -> list[EvidenceRecord]: ...
    async def mark_hashed(self, record: EvidenceRecord) -> EvidenceRecord: ...
    async def seal(self, record: EvidenceRecord) -> EvidenceRecord: ...
    async def set_legal_hold(self, record: EvidenceRecord) -> EvidenceRecord: ...
