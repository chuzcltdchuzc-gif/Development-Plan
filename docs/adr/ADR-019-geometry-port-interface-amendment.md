# ADR-019 — GeometryPort Interface Amendment (Tenant/Parcel-Scoped Reference Validation)

**Status:** **Accepted.** Reviewed and approved in full — this is **the first formal amendment
of the B4 (Spatial Intelligence) programme**: the first time a B4 decision reaches back into
already-frozen B1–B3 code, and the first exercise of this codebase's amendment discipline
(ADR-011/012/017) in the direction of extending a *contract*, rather than merely restating that
a later bounded context reuses one unchanged. `docs/adr/ADR-016-geometry-port-boundary-spatial-integration.md`
is preserved unmodified as historical context — it correctly records what B3 decided at the time
B3 shipped — while this document is the authoritative, citable record of how that decision has
since evolved. `GeometryPort`'s signature change, `PlaceholderGeometryAdapter`'s corresponding
update, and the one touched call site in `ParcelService` are implemented as part of this
acceptance (§"Implementation evidence," below) — narrowly, per the approved scope: no validation
algorithm, no overlap detection, and no other GIS functionality is introduced here; those remain
ADR-020/021's job, unwritten. B4 Slice 1 — Spatial Domain Foundation is authorized to begin
following this acceptance.

**Date:** 2026-07-22

**Scope:** One interface signature change only —
`app.contexts.registry.ports.GeometryPort.reference_is_valid` — and the one call site that
invokes it, `app.contexts.registry.application.parcel_service.ParcelService.set_geometry_reference`.
Nothing else. This ADR does not define what "valid" means (ADR-020), does not implement overlap
detection (ADR-021), and does not touch any other part of `docs/adr/ADR-016-geometry-port-boundary-spatial-integration.md`
or `docs/adr/ADR-017-b3-platform-freeze.md`.

## Why this is its own ADR, not a subsection of ADR-018

`docs/adr/ADR-018-spatial-domain-model.md` is a Spatial-context (B4) decision — everything else
in it is new code, in a new bounded context, that does not exist yet and therefore cannot violate
anything already shipped. This one change is different in kind: it modifies the call signature of
a contract already accepted and frozen as part of B3 (`docs/adr/ADR-017-b3-platform-freeze.md`),
and it requires editing one line of already-shipped, already-tested, already-frozen Registry code
(`ParcelService.set_geometry_reference`'s call to `self.geometry.reference_is_valid(...)`). This
codebase's amendment discipline — established in ADR-011, restated in ADR-012 and ADR-017 —
requires exactly this: *"a bounded context that needs [a frozen decision] to behave differently
opens a new ADR referencing it and states precisely what changes and why. It does not edit the
source directly as a side effect."* Folding this into ADR-018 would satisfy the letter of that
rule (ADR-018 does reference ADR-016 and does state what changes and why, in its §5) but not the
spirit of the explicit instruction governing this specific step: that a change reaching back into
frozen B3 code gets reviewed and approved as its own, clearly identifiable record — easy to find
in git history and in `docs/adr/` without having to read all of ADR-018 to discover that B3 code
was touched at all.

## Context

`GeometryPort` (ADR-016) is defined as:

```python
class GeometryPort(Protocol):
    async def reference_is_valid(self, *, geometry_reference: str) -> bool: ...
```

`PlaceholderGeometryAdapter` (B3 Slice 4) satisfies this by always returning `True` — it validates
nothing, so the signature's limitations were invisible until ADR-018 designed a **real** adapter.
A real adapter is backed by `ParcelGeometry` (ADR-018) — rows keyed by `geometry_id`, each
belonging to exactly one `tenant_id` and `parcel_id`. Given only a bare `geometry_reference`
string, a real adapter can answer *"does a `ParcelGeometry` row with this `geometry_id` exist
anywhere, for any tenant"* — but it cannot answer the question that actually matters to Registry:
*"does this reference belong to the tenant and parcel currently attempting to attach it."*

**The concrete leak this closes:** without tenant/parcel scoping, tenant A could attach tenant
B's `geometry_reference` to tenant A's own parcel — merely by guessing, observing, or otherwise
obtaining a valid-looking `geometry_id` — and the real adapter, as specified by the unamended
interface, would have no way to detect or refuse this, because it is never told which tenant or
parcel is asking. This is not a hypothetical hardening exercise; it is the direct, structural
consequence of building a real adapter against the interface exactly as ADR-016 left it, and
`docs/B4_THREAT_MODEL.md` §5 (TB3, "Information disclosure") already flagged the general shape of
this risk before ADR-018 made it concrete.

## Decision

### The amended signature

```python
class GeometryPort(Protocol):
    async def reference_is_valid(
        self, *, geometry_reference: str, tenant_id: str, parcel_id: str
    ) -> bool: ...
```

`tenant_id` and `parcel_id` are the caller's own already-authorized context — the `parcel_id`
already being mutated in the same `ParcelService.set_geometry_reference` call, and the tenant
that *owns* it — not new input the caller doesn't already possess. A real adapter's
implementation checks that the `ParcelGeometry` row matching `geometry_reference` has exactly
this `tenant_id` and `parcel_id`; any mismatch (wrong tenant, wrong parcel, or no such row at
all) returns `False`, indistinguishable from any other invalid reference — the port still
returns only a plain boolean (unchanged from ADR-016, and consistent with
`docs/B4_THREAT_MODEL.md` §6's requirement that the adapter's failure mode never leak richer
diagnostic detail through Registry's error surface).

### The one code touchpoint

`ParcelService.set_geometry_reference` (`backend/app/contexts/registry/application/parcel_service.py`,
frozen B3 Slice 4 / ADR-015 / ADR-016) called:

```python
valid = await self.geometry.reference_is_valid(geometry_reference=geometry_reference)
```

and, as implemented under this ADR's acceptance, now calls:

```python
valid = await self.geometry.reference_is_valid(
    geometry_reference=geometry_reference,
    tenant_id=parcel.tenant_id,
    parcel_id=parcel_id,
)
```

**`parcel.tenant_id`, not `ctx.tenant_id`** — a refinement made during implementation, not part
of the original proposal above. `ExecutionContext.tenant_id` is typed `str | None` (an anonymous
or tenant-less context is structurally possible), and more importantly, the actual question this
check answers is *"does this reference belong to the tenant that owns this parcel,"* which for a
`super_admin` acting cross-tenant is `parcel.tenant_id`, not necessarily the acting principal's
own tenant. `parcel.tenant_id` is always defined (the parcel is already loaded via
`_load_in_scope` by this point) and is the semantically correct value regardless of which caller
tier is acting — confirmed by `mypy` rejecting the original `ctx.tenant_id` draft outright
(`str | None` where `str` was required), which is exactly the kind of real, non-speculative
correctness check this codebase's "never mark complete without observing it pass" discipline
exists to catch before it ships, not after.

Both `parcel.tenant_id` and `parcel_id` are already in scope at this call site — nothing new is
threaded in from outside the method, no new dependency, no new parameter on
`set_geometry_reference` itself. `PlaceholderGeometryAdapter.reference_is_valid`'s signature
gained the same two keyword-only parameters and continues to ignore them, returning `True`
unconditionally — its behavior is unaffected; it simply accepts (and disregards) more context,
exactly as a stub implementing a real protocol should. `FakeGeometryPort` (tests) gained the same
two parameters, deliberately not adding them to its `.calls` recording — no existing test
assertion needed to change as a result (confirmed, not assumed — see "Implementation evidence,"
below).

### Why additive, not breaking

`GeometryPort` has exactly two implementers today (`PlaceholderGeometryAdapter`,
production; `FakeGeometryPort`, tests) and exactly one consumer (`ParcelService`). Both
implementers are within this codebase's control and are updated in the same change; no
third-party or external caller exists to break. This is the same reasoning ADR-011 used when
extending `ExecutionContext.attributes` — a contract with a small, fully-enumerable set of
implementers can be safely extended in place rather than versioned.

## Alternatives considered and rejected

1. **Leave the signature unchanged; verify tenant/parcel ownership inside `ParcelService`
   instead.** Rejected in ADR-018 §5 and restated here: `ParcelService` has no access to
   `ParcelGeometry`'s data (a different bounded context) and cannot verify a fact only Spatial's
   own repository knows. This would either require Registry to reach into Spatial's tables
   directly (violating the ADR-016 boundary both ADR-018 and this ADR are built on top of) or
   silently permit the leak described above.
2. **A new, second port method** (e.g., `reference_belongs_to(geometry_reference, tenant_id,
   parcel_id) -> bool`) **alongside the unchanged `reference_is_valid`.** Rejected: this would
   mean two port methods answering overlapping questions, with no clear rule for which one a
   future caller should use — exactly the kind of interface sprawl "ports before adapters, no
   speculative abstractions" (ADR-016, restated) warns against. One method, correctly scoped, is
   simpler than two, narrower ones with unclear boundaries between them.
3. **Version the protocol** (`GeometryPortV2`) **rather than amend it in place.** Rejected as
   unnecessary ceremony given both implementers are updated together in the same change — see
   "Why additive, not breaking," above. Versioning matters when a contract has callers outside
   this codebase's control; `GeometryPort` does not.

## Relationship to the frozen baseline

- **ADR-016** — this is a formal, disclosed amendment to `GeometryPort`'s signature, not a
  reinterpretation of what the port is for (still: "does this reference make sense to attach,"
  never geometry content itself). Every other part of ADR-016 — the port's existence, its
  minimalism, the placeholder-adapter pattern, the "Registry never depends on PostGIS directly"
  principle — is unchanged.
- **ADR-017 (B3 freeze)** — the one line changed in `ParcelService.set_geometry_reference` is
  B3-frozen code. This ADR is the explicit authorization required to touch it, per B3's own
  amendment discipline ("no further B3-scope changes land without a new ADR referencing
  ADR-013/014/015/016/017").
- **ADR-018** — this ADR fulfills the extension ADR-018 §5 identified and deferred to its own
  record; ADR-018's own content is otherwise unaffected.
- **No other frozen decision is touched.**

## Consequences

- ADR-020 (real `GeometryPort` adapter & validation rules) can be written and implemented against
  a signature that actually supports correct tenant/parcel-scoped validation, rather than
  inheriting the placeholder-era signature's blind spot.
- **B3's frozen test suite for `ParcelService` required zero changes** (confirmed, §"Implementation
  evidence," below) — `PlaceholderGeometryAdapter` and `FakeGeometryPort` both accept the new
  parameters and ignore them for behavior/recording purposes, so every existing assertion against
  either still holds unmodified. This was a design goal (§"Why additive, not breaking"), not
  merely a hope.
- This is now the documented precedent for how a future B4+ ADR should propose touching frozen
  B1–B3 code going forward: identify the need in the ADR that discovers it (as ADR-018 §5 did),
  then formally record the actual amendment as its own dedicated ADR before implementing it.

## Implementation evidence

Implemented in full under this ADR's acceptance — `GeometryPort.reference_is_valid`
(`app/contexts/registry/ports.py`), `PlaceholderGeometryAdapter`
(`app/contexts/registry/adapters/geometry.py`), `ParcelService.set_geometry_reference`
(`app/contexts/registry/application/parcel_service.py`, using `parcel.tenant_id` per the
refinement above), and `FakeGeometryPort` (`tests/fakes/registry.py`) all updated. No validation
algorithm, overlap detection, or other GIS functionality was introduced — strictly the signature
change and its one call site, per the approved scope.

- Full `ruff check .`: clean.
- Full `mypy .`: clean, 88 source files (initially caught the `ctx.tenant_id` vs. `parcel.tenant_id`
  type error described above — fixed before this evidence was recorded, not after).
- Full `pytest` suite: **119/119 passed**, zero test file changes required.
- Geometry-specific tests (`test_b3_registry.py -k geometry`): **9/9 passed**, confirming the
  amendment holds for every previously-verified scenario (attach, detach, ownership reuse,
  cross-tenant denial, archived-parcel denial, port-rejection, audit) without alteration.

## Approval Gate

This ADR is **accepted**, and its implementation is complete and verified (above). B4 Slice 1 —
Spatial Domain Foundation is authorized to begin, per `docs/B4_DISCOVERY_AND_PLANNING.md` §4's
Slice B4.1 scope.
