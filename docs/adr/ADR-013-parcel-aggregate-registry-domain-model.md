# ADR-013 — Parcel Aggregate and Registry Domain Model

**Status:** Accepted — extends ADR-009, ADR-010, ADR-011, ADR-012. Does not amend any frozen
decision; see §"Relationship to the frozen baseline" for exactly which mechanisms are reused
unchanged and why none required modification.

**Date:** 2026-07-18

**Scope:** B3 Slice 1 only — `backend/app/contexts/registry/`, migration
`0007_parcels.py`. Slices 2–4 (atomic numbering, mutation commands, geometry port) are
explicitly out of scope for this ADR's implementation claims, though this document states the
invariants they must honor when they land.

## Context

`docs/REBUILD_PLAN.md` §1 assigns B3 = Registry: "canonical parcel aggregate, ownership
history, parcel numbering." `docs/adr/ADR-005-property-registry-data-model.md` already
decided the shape this aggregate should take — one canonical `LandVault`-style aggregate (not
Base44's confirmed-defective two-parallel-entity design), immutable core fields, an atomic
allocator, and real actor-identity authorization (fixing a confirmed historical vulnerability:
Emergent's PDP resource descriptor never carried `created_by`, so any create-tier role could
mutate any parcel in their tenant). `docs/B3_DISCOVERY_AND_PLANNING.md` §5 proposed this ADR.
This document is Slice 1's design: the aggregate's foundation, before numbering (Slice 2),
mutation commands (Slice 3), or the geometry port (Slice 4) exist.

**Field grounding:** the audit corpus (`docs/audits/AQUASAVANNAH_LANDVAULT_FORENSIC_AUDIT.md`)
lists a representative, non-exhaustive subset of Base44's `LandParcel`/`LandVaultParcel`
fields (95+/60+ fields total, ~48/~34 named). No exhaustive schema exists in the audits. This
ADR draws only the fields that belong to *registry identity/metadata* specifically — GPS/
geometry, evidence/consent, survey, payment, and trust/confidence fields are excluded because
they belong to later bounded contexts (B4–B7, B9, B11), not because they were overlooked.

## Decision

### The Parcel aggregate

`Parcel` (`app.contexts.registry.domain.parcel`) is the single, canonical representation of a
land parcel. `parcel_id` (a UUID, matching every other aggregate's `<name>_id` convention in
this codebase) is its immutable identity, generated at construction and never reassigned.

**Owned by the aggregate (Slice 1):** identity (`parcel_id`, `tenant_id`, `country_code`,
`origin`, `created_at`/`created_by`), lifecycle (`status`: `ACTIVE`/`ARCHIVED`, terminal),
registry metadata (`title`, `address`, `state`/`lga`/`ward`/`community` — free-text
administrative location, not computed/validated geometry, `property_type`, `size_sqm` as a
self-declared figure, `ownership_type`), and a **current ownership reference**
(`current_owner_name`, `current_owner_contact` — who owns it *now*, not the history of who
has owned it). `parcel_number` exists as a nullable column, reserved for Slice 2.

**Not owned by the aggregate, deliberately, per the B3 Slice 1 authorization:** survey plans,
evidence, GPS/geometry processing, notifications, payments, AI, and — explicitly — ownership
history *as a record of past transfers* (only the *current* reference lives here; the
append-only history itself is a later slice's responsibility, kept a distinct concept from
day one so it never gets conflated with "who owns it now").

**No PII beyond what's already necessary.** `current_owner_name`/`current_owner_contact` are
free-text descriptive fields; nothing resembling Base44's `owner_nin` (a field the audit
corpus explicitly flags `PRIVATE`) is included. Handling genuinely sensitive PII needs its own
encryption-at-rest strategy (the same open question `Session.idp_refresh_token`'s docstring
already flags as B13 Security hardening work) — not something Slice 1 takes on implicitly by
adding a sensitive field without that strategy existing.

### Domain invariants (enforced as domain rules, not endpoint validation)

1. **Parcel identity is immutable** — `parcel_id` is set once, at construction, never
   reassigned; there is no setter for it anywhere in the domain or application layers.
2. **Parcel number, once allocated, can never be reassigned** — `allocate_parcel_number()`
   raises if `parcel_number` is already set. The method exists now (Slice 1), unused by any
   Slice 1 API path, as the guarded mutation point Slice 2's real allocator will call — this
   is what "reserve the field" means concretely: not a bare mutable column, a protected one.
3. **A Parcel is never duplicated** — `parcel_id` is the primary key (trivially unique); a
   partial unique index on `parcel_number WHERE parcel_number IS NOT NULL` enforces
   uniqueness at the database level *before* Slice 2's allocator exists, so uniqueness is
   never a retrofit.
4. **Ownership transfer never creates a new Parcel** — a binding constraint on Slice 3: any
   future `record_ownership_transfer`-style command must mutate `self` in place, never
   construct a new `Parcel`. Nothing in Slice 1 violates this since no transfer command exists
   yet; stated here so Slice 3 is bound by it from design, not discovered as a bug later.
5. **Geometry changes never create a new Parcel** — the same constraint, binding on Slice 4.
6. **Archived Parcels cannot be modified** — `_ensure_mutable()` raises `ParcelArchivedError`
   if `status == ARCHIVED`; every mutator (currently only `allocate_parcel_number`) calls it
   first. No `archive()` command is exposed via any API in Slice 1 (that's a mutation command,
   explicitly out of scope) — the guard exists and is unit-tested directly against the domain
   object (constructing a `Parcel` with `status=ARCHIVED` and asserting the mutator refuses),
   proving the rule as a domain invariant without needing the command that triggers it yet.
7. **Every mutation creates an immutable audit event** — `create_parcel` calls the kernel
   `audit()` function (`registry.parcel.created`), the exact mechanism ADR-007/ADR-009
   established; no second audit mechanism.
8. **Authorization is evaluated before every mutation** — `require_role(*PARCEL_REGISTRANT_ROLES)`
   gates `POST /v1/parcels` before the application service or domain object are ever reached.
9. **Tenant isolation is absolute** — RLS (same policy shape as every tenant-scoped table
   since migration `0001`) plus an explicit application-layer tenant filter, the same
   two-independent-layers pattern ADR-009/010/011 already established.
10. **No Parcel command bypasses the existing PDP** — see §"Authorization flow" below; there
    is no second authorization path anywhere in Registry.
11. **Parcel history is append-only** — binding on the (not-yet-built) ownership-history
    mechanism; Slice 1 has no history table yet, so nothing here violates it, but the
    constraint is recorded for whichever slice builds it.
12. **Registry identity and ownership history are distinct concepts** — `parcel_id` (identity)
    and `current_owner_name`/`current_owner_contact` (a *reference*, not a *history*) are
    modeled as clearly separate concerns from the start, so a future ownership-history table
    is additive, not a refactor of the identity fields.

### Authorization flow — unchanged, only a new consumer

Registry introduces no new authorization mechanism. The flow is exactly what ADR-009/010/011
already established:

```
Identity (verified JWT) -> Context Hydration (user + tenant + delegation resolution,
app.contexts.identity.context_hydration) -> ExecutionContext.roles -> require_role /
require_auth (app.kernel.authorization.pep) -> Registry application service -> Parcel domain
object
```

`POST /v1/parcels` is gated `require_role(*PARCEL_REGISTRANT_ROLES)` —
`field_agent`, `licensed_surveyor`, `surveyor_partner`, `surveyor_general`,
`compliance_officer`, `super_admin` (defined in `registry.domain.value_objects`, referencing
Identity's existing `Role` enum values — no new role, no duplicated string literal). `GET`
endpoints use bare `require_auth` — tenant-scoped visibility is enforced by RLS and an
explicit repository-level tenant filter, not a role gate, matching how `GET /v1/auth/me`
already works. A delegate holding a delegated `field_agent`/`licensed_surveyor`/etc. role
(ADR-011) can register a parcel exactly as if they held it directly — `require_role` doesn't
know or care whether a role in `ExecutionContext.roles` came from a direct grant or a live,
currently-effective delegation; this is the delegation design working exactly as ADR-011
intended, not a new integration point.

### RLS — the same policy shape, not a Parcel-specific variant

`parcels` gets `FORCE ROW LEVEL SECURITY` and the identical policy text every tenant-scoped
table has used since migration `0001`:
`tenant_id = current_setting('app.tenant_id', true) OR current_setting('app.is_super_admin',
true) = 'true'`. This means a `super_admin` can see parcels across tenants at the database
layer — exactly as they already can for `identity_users`/`tenants`/`identity_invitations`/
`identity_delegations`. "Cross-tenant visibility is prohibited" (Slice 1's own stated
invariant) binds ordinary tenant-scoped principals, not the platform-operator bypass every
other RLS policy already grants; carving out a Parcel-specific narrower RLS shape would mean
diverging from the frozen RLS model, which this ADR does not do. `list_parcels` itself stays
strictly tenant-scoped (queries `list_for_tenant(ctx.tenant_id)` regardless of caller role) —
no cross-tenant "list all parcels" capability is built in Slice 1; that would be a speculative
feature with no requirement behind it yet.

### A known, small, deliberate duplication

`AdminService._in_scope()` (Identity, B2 slice 4/ADR-011) — the `tenant_id == ctx.tenant_id OR
super_admin` check — is duplicated locally in Registry's application service rather than
imported, because it is a private (`_`-prefixed) helper internal to `admin_service.py`, and
importing a private symbol across a context boundary is worse than a three-line duplication.
If a third context needs the identical check, that's the trigger to promote it into the
kernel via its own small ADR — not presupposed here (rule of three, not premature
abstraction).

## Relationship to the frozen baseline

- **ADR-009** — PDP/PEP, Unit-of-Work, RLS session-variable mechanism, audit chain: all
  consumed unchanged. Registry is a new *consumer* of these kernel mechanisms, not a modifier
  of them.
- **ADR-010** — `parcels.tenant_id` is a real FK to `tenants.id` *from its first migration*
  (unlike Identity's own `tenant_id`, which started as a bare string and only got FK'd
  retroactively in B2 slice 3) — Registry starts from the corrected pattern rather than
  repeating the historical detour.
- **ADR-011** — delegated roles work transparently for Registry authorization, as described
  above, with zero Registry-specific integration code.
- **ADR-012** — no Identity/Tenant/Delegation/Administration file is modified by this slice.
- **No frozen decision required amendment.**

## Consequences

- Slice 2 (atomic parcel numbering) has a guarded, tested mutation point
  (`allocate_parcel_number()`) to call into — it does not need to design the "can this be
  reassigned" rule itself, only the concurrency-safe number-generation mechanism.
- Slice 3 (mutation commands, real actor-identity authorization) inherits the `_ensure_mutable`
  archived-guard pattern and the `created_by` field already present on every parcel — the
  confirmed ADR-005 defect (resource descriptor never carrying `created_by`) has no
  opportunity to recur, since the field exists and is populated from the first parcel ever
  created.
- Slice 4 (geometry port) has a clean seam: `Parcel` has no geometry field yet, deliberately,
  so B4 adds it without needing to touch or migrate around a placeholder column.
- The `_in_scope` duplication (§ above) is a tracked, minor, deliberate decision — not
  technical debt introduced silently.
