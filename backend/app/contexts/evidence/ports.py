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

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from app.contexts.evidence.domain.attribution import EvidenceActorAttribution
from app.contexts.evidence.domain.evidence_record import EvidenceRecord

WormGrade = Literal["governance", "compliance"]


@dataclass(frozen=True)
class ParcelAuthorityInfo:
    """The minimum information the Evidence upload authorization check
    (IMVP-5) needs about the parcel an upload targets — tenant scope and
    creator authority, the identical shape docs/adr/ADR-022 §8 already
    established for Spatial's own ParcelExistencePort
    (app.contexts.spatial.ports). Duplicated here, not imported, per the
    same bounded-context isolation reasoning (docs/adr/ADR-018): Evidence
    has no need for, and must not depend on, anything else about a
    parcel."""

    tenant_id: str
    created_by: str


class ParcelExistencePort(Protocol):
    """Read-only existence/authority lookup against Registry's `parcels`
    table — the one place Evidence reads across the context boundary,
    mirroring app.contexts.spatial.ports.ParcelExistencePort exactly.
    Returns `ParcelAuthorityInfo` if the parcel exists (and, for the real
    adapter, is visible under `parcels`' own RLS policy), `None`
    otherwise."""

    async def get_parcel_authority(self, *, parcel_id: str) -> ParcelAuthorityInfo | None: ...


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


class EvidenceActorAttributionRepository(Protocol):
    """The EvidenceActorAttribution value object's persistence port (ADR-028
    "EvidenceActorAttribution relationship"). Deliberately narrow, mirroring
    app.contexts.registry.ports.ParcelHistoryRepository's shape: no
    generic update/delete method exists on this Protocol at all — rows are
    append-only by construction, not only by the database grant/trigger
    (migrations/versions/0014). `get_successor` exists so the application
    service can walk a lineage forward to its current active head without
    itself tracking history state — the same "ask the repository, don't
    duplicate its state" shape ParcelHistoryRepository already established
    (`latest_ownership`/`latest_status`)."""

    async def record(self, attribution: EvidenceActorAttribution) -> EvidenceActorAttribution: ...
    async def get(self, attribution_id: str) -> EvidenceActorAttribution | None: ...
    async def list_for_evidence(self, evidence_id: str) -> list[EvidenceActorAttribution]: ...
    async def get_successor(self, attribution_id: str) -> EvidenceActorAttribution | None: ...


class PrincipalTenantPort(Protocol):
    """Read-only tenant lookup for an Identity principal — the one place
    Evidence's attribution service reads across the Identity context
    boundary, mirroring ParcelExistencePort's exact shape and reasoning
    (a minimal, read-only, Evidence-defined port; Identity is never
    imported directly). Used only to enforce ADR-028's same-tenant rule
    for `actor_principal_id`: a live internal reference is permitted only
    when it resolves to a principal in the same tenant as the Evidence
    being attributed. Returns `None` if `principal_id` does not resolve to
    any known principal."""

    async def get_tenant_id(self, principal_id: str) -> str | None: ...
