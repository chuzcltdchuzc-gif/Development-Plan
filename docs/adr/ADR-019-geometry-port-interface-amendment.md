# ADR-019 — GeometryPort Interface Amendment (Tenant/Parcel-Scoped Reference Validation)

**Status:** Proposed — drafted under explicit authorization to formally record the amendment
`docs/adr/ADR-018-spatial-domain-model.md` §5 identified. Not yet reviewed or accepted.
**No B4 code exists; this document authorizes no implementation on its own.** Per the governing
instruction, the `GeometryPort` signature change described below does not happen — and B4 Slice
1 does not begin — until this ADR is itself reviewed and explicitly accepted, separate from
ADR-018's own acceptance.

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

`tenant_id` and `parcel_id` are the caller's own already-authorized context — `ctx.tenant_id` and
the `parcel_id` already being mutated in the same `ParcelService.set_geometry_reference` call —
not new input the caller doesn't already possess. A real adapter's implementation checks that the
`ParcelGeometry` row matching `geometry_reference` has exactly this `tenant_id` and `parcel_id`;
any mismatch (wrong tenant, wrong parcel, or no such row at all) returns `False`, indistinguishable
from any other invalid reference — the port still returns only a plain boolean (unchanged from
ADR-016, and consistent with `docs/B4_THREAT_MODEL.md` §6's requirement that the adapter's failure
mode never leak richer diagnostic detail through Registry's error surface).

### The one code touchpoint

`ParcelService.set_geometry_reference` (`backend/app/contexts/registry/application/parcel_service.py`,
frozen B3 Slice 4 / ADR-015 / ADR-016) currently calls:

```python
valid = await self.geometry.reference_is_valid(geometry_reference=geometry_reference)
```

and will call, once this ADR is accepted and implemented:

```python
valid = await self.geometry.reference_is_valid(
    geometry_reference=geometry_reference, tenant_id=ctx.tenant_id, parcel_id=parcel_id
)
```

Both `ctx.tenant_id` and `parcel_id` are already in scope at this call site — nothing new is
threaded in from outside the method, no new dependency, no new parameter on
`set_geometry_reference` itself. `PlaceholderGeometryAdapter.reference_is_valid`'s signature
gains the same two keyword-only parameters and continues to ignore them, returning `True`
unconditionally — its behavior is unaffected; it simply accepts (and disregards) more context,
exactly as a stub implementing a real protocol should.

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
- B3's frozen test suite for `ParcelService` (Slice 3/4 tests) gains two additional call-site
  arguments to account for once this is implemented — an additive test update, not a rewrite of
  existing assertions, since `PlaceholderGeometryAdapter`'s always-`True` behavior is unchanged.
- This is now the documented precedent for how a future B4+ ADR should propose touching frozen
  B1–B3 code going forward: identify the need in the ADR that discovers it (as ADR-018 §5 did),
  then formally record the actual amendment as its own dedicated ADR before implementing it.

## Approval Gate

This ADR is **proposed**, not accepted. Implementation — the signature change on `GeometryPort`,
`PlaceholderGeometryAdapter`, `FakeGeometryPort`, and the one call site in `ParcelService` — does
not begin until this document is reviewed and explicitly accepted. B4 Slice 1 does not begin
until then either, since Slice 1's own scope (`docs/B4_DISCOVERY_AND_PLANNING.md` §4, Slice B4.1)
depends on this amendment being in place.
