# Platform Intelligence — Long-Term Architecture

**Type:** Architectural documentation, **not an ADR** — this describes how a concept ADR-021 §6
introduces (platform intelligence services) fits into the platform's overall shape. It authorizes
no implementation; the only Platform Intelligence capability with any governing document at all is
Spatial Conflict Detection (`docs/adr/ADR-021-...md`, `docs/SCDS-001-...md`), and even that remains
unaccepted/unimplemented.

**Date:** 2026-07-24

**Governed by:** ADR-021 §6 (the "platform intelligence services, not domain entities" doctrine
this document names and diagrams), `docs/ENGINEERING_RULES.md` rule 9 (Controlled Platform
Authority — the mechanism every Platform Intelligence capability must use to see across bounded
contexts), `docs/REBUILD_PLAN.md` §1 (the 13 bounded contexts this layer sits alongside, never
inside).

## What Platform Intelligence is

**Platform Intelligence is not a bounded context.** It introduces no new aggregate, no new
tenant-scoped table owned by "Platform Intelligence" itself, and no fourteenth entry in
`docs/REBUILD_PLAN.md`'s context list. It is a **collection of platform services** — code that
reads across bounded-context boundaries (and, narrowly, across tenant boundaries) to produce a
signal, finding, or score *about* the domains beneath it, without ever owning or redefining those
domains' own data.

This is not a new architectural pattern for this platform — it is the explicit naming of a
pattern this platform already has one instance of (the Trust Engine, `docs/REBUILD_PLAN.md` B7,
"aggregating signals from every context below as they land") and is about to gain a second
instance of (Spatial Conflict Detection, ADR-021, if accepted). Naming the layer now, before a
second instance is built, is what lets both instances share one doctrine instead of each
inventing its own cross-context-read justification independently.

## Position in the platform

```
Platform Kernel (ADR-002/ADR-009 — auth, audit, RLS enforcement, request lifecycle)
│
├── Identity            (B1 — tenants, users, roles, delegation)
├── Registry             (B3 — Parcel aggregate, parcel identity, ownership)
├── Spatial               (B4 — ParcelGeometry aggregate, geometry validation, per-tenant authorization)
├── Evidence              (B5 — not yet built)
├── Authorization          (the PDP/PEP/PIP engine — ADR-004, cross-cutting, used by every context above)
├── Audit                  (the kernel audit() mechanism — ADR-007, cross-cutting, used by every context above)
│
└── Platform Intelligence  (cross-cutting services — reads across the contexts above, owns none of them)
    ├── Conflict Engine     (ADR-021/SCDS-001 — proposed, not built: Spatial's cross-tenant geometry comparison)
    ├── Fraud Engine        (not designed — a future consumer of Conflict Engine findings, per ADR-021 §6/§8)
    ├── Risk Engine          (not designed — the Trust Engine's own scoring, B7, is this platform's only
    │                          existing example of this shape; a Spatial-specific risk score, if ever built,
    │                          is a second instance under this same doctrine, per SCDS-001 §3)
    ├── AI Engine            (not designed — any future ML capability)
    ├── Analytics Engine     (not designed — any future cross-context reporting capability)
    └── Compliance Engine    (not designed — any future regulatory/audit-reporting capability)
```

**Reading this diagram correctly:** the six named engines under Platform Intelligence are *not*
six things this platform is committing to build. Only the Conflict Engine has any governing
document at all (ADR-021, proposed), and even it is unimplemented. The other five are named so
that *if* they are ever built, their designers inherit this document's doctrine rather than each
independently re-deriving "how do we safely read across bounded contexts" from scratch — the
exact re-derivation risk that produced the original, ungoverned Base44/Emergent authorization
defects this entire rebuild exists to close (`docs/audits/`).

## What makes a capability "Platform Intelligence" rather than a domain service

A capability belongs under Platform Intelligence, not inside Registry or Spatial (or any future
domain context), if and only if it satisfies **all** of:

1. **It reads across more than one bounded context, or across more than one tenant, in a single
   logical operation.** A capability that only ever touches one context's own data, one tenant at
   a time, is that context's own domain service — not Platform Intelligence. (Spatial's existing
   `submit_geometry`/`get_active_geometry` are Spatial domain services, not Platform Intelligence,
   under this test — they never compare across tenants.)
2. **It produces a finding, signal, or score *about* the domains it reads — never a mutation of
   their own aggregates' fields.** Per ADR-021 §6: no "conflict status" is ever added to
   `ParcelGeometry`; no "trust score" field is ever added to `Parcel`. A Platform Intelligence
   finding is its own data, referencing the domain entities it describes by identifier.
3. **Its cross-context/cross-tenant read is a named, narrow, Controlled Platform Authority
   exception** (`docs/ENGINEERING_RULES.md` rule 9) — never a blanket cross-tenant grant, and
   never inherited from another capability's own exception (ADR-021 §1's "no second exception
   inherits this one," restated as a platform-wide rule here, not merely a Spatial-specific one).
4. **Its output is consumed by other contexts only through a narrow, pre-scoped signal
   interface** — never by a downstream context querying the underlying cross-tenant data
   directly. This is the same requirement `docs/B4_THREAT_MODEL.md` TB6 already states for the
   Trust Engine (B7) consuming Spatial's duplicate-geometry signal; this document generalizes it
   to every Platform Intelligence capability, present or future.

## What Platform Intelligence is not

- **Not a bounded context** — it owns no aggregate, has no `tenant_id`-scoped table of its own by
  default (a finding record, e.g. a conflict finding, is closer to an audit-adjacent artifact than
  a domain aggregate — its own data model, if any, is Slice 3/SCDS-001's job to define, not this
  document's).
- **Not a replacement for RLS or the PDP/PEP authorization pipeline** — every Platform
  Intelligence capability's *ordinary* read/write (the part that stays within one tenant) still
  goes through the exact same RLS and authorization path every other context uses; only the
  narrow, named cross-tenant portion is a Controlled Platform Authority exception, never a
  wholesale bypass of the pipeline.
- **Not a business domain** — "Fraud Engine," "Risk Engine," etc. are capability names, not
  domains with their own ubiquitous language, aggregates, or product requirements independent of
  the contexts they observe. If a future need proves one of these deserves to become a genuine
  bounded context in its own right (with its own aggregates, its own domain rules), that is a
  distinct architectural decision requiring its own ADR — this document does not pre-decide it
  either way, and today, nothing built or proposed (ADR-021/SCDS-001 included) meets that bar.

## Relationship to existing ADRs

- **ADR-021** is this layer's first proposed instance (Conflict Engine) and the source of the
  four-part test above (generalized from ADR-021 §1/§6's Spatial-specific reasoning).
- **`docs/ENGINEERING_RULES.md` rule 9** (Controlled Platform Authority) is the security doctrine
  every Platform Intelligence capability's cross-context read must satisfy — this document does
  not weaken, restate differently, or add a second version of that rule.
- **`docs/REBUILD_PLAN.md` B7 (Trust Engine)** is retroactively recognized as this platform's
  first Platform Intelligence-shaped capability, once it exists — no change to B7's own scope or
  design is made by this document; it is named here only so that B7 and the Conflict Engine (if
  accepted) share one doctrine rather than two independently-invented ones.

## Consequences of naming this layer now

- Any future capability proposal that reads across bounded contexts or tenants must be evaluated
  against the four-part test above before it is designed — this is now a standing architectural
  review question, the same way "does this need Controlled Platform Authority" already is.
- No implementation changes as a result of this document. It records a naming and a doctrine, not
  a build.
