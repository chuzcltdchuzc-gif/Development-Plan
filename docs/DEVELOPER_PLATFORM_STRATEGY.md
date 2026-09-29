# Developer Platform — Planning Recommendation

**Type:** Planning recommendation only. **No code, migration, API, bounded context, or ADR is
introduced by this document.** Named in `docs/ARCHITECTURE_HANDBOOK.md` Part VIII as a future
programme with no current scoping; this document is that scoping's starting point, not its
resolution.

**Date:** 2026-07-25

**Governed by:** `docs/PLATFORM_STRATEGY.md` (the Developer Portal concept; the multi-sided
platform model this programme is the technical enabler for), `docs/adr/
ADR-004-authentication-authorisation-model.md` (the authentication model this programme would
extend, not replace, for a new non-human principal type), `docs/ENGINEERING_RULES.md` rule 9
(any API surface exposing more than one tenant's data is a Controlled Platform Authority question,
not merely an API-design question).

## Why this and API Ecosystem are named together

`docs/ARCHITECTURE_HANDBOOK.md` Part VIII already observed that "Developer Platform" and "API
Ecosystem" are likely the same underlying capability viewed from two angles: Developer Platform is
the *producer*-facing concern (how does LandVault expose itself so third parties can build on it);
API Ecosystem is the *consumer*-facing concern (what gets built using that exposure, and how it is
governed once it exists). This document treats them as one planning exercise for that reason,
rather than producing two documents that would need to agree with each other immediately.

## Objectives

1. Establish a non-human principal type — an API credential/key, distinct from a human `User` —
   before any public API surface is built. This is an extension of Identity's existing
   authentication model (`docs/adr/ADR-004-...md`, ADR-009), not a second authentication mechanism
   — this platform's "exactly one authorization path" rule (`docs/ENGINEERING_RULES.md` rule 1)
   applies to *how* a request is authorized once authenticated, regardless of whether the
   authenticated principal is a human or a service account; it does not imply only humans may ever
   authenticate.
2. Determine which capabilities are safe to expose externally at all, and at what disclosure
   level, before any endpoint is designed — a public-facing API is a materially different threat
   model than this platform's current authenticated-tenant-user model (every RLS policy assumes a
   session-scoped `tenant_id`; a third-party developer's API key needs its own, likely narrower,
   scoping model, not an assumption that "authenticated" automatically means "full tenant reach").
3. Define sandbox/production separation — a developer needs to build and test against realistic
   data without ever touching real registrants' real parcels; this is a new environment-isolation
   concern this platform has not needed before (its existing three environments — dev/staging/
   production, `docs/PHASE_GATES.md` Phase 2 — are deployment environments, not a
   third-party-facing sandbox with its own synthetic dataset).
4. Establish webhook delivery as its own reliability concern — a webhook is this platform pushing
   data to a third party's own system, the reverse direction of every integration this platform has
   built so far (Registry→Spatial via `dependency_overrides` is internal composition-root wiring;
   a webhook to an external developer's endpoint has no equivalent trust boundary and needs its own
   retry/failure/security (signature verification) model, mirroring the audited-correct webhook
   signature-verification pattern already reused from the Emergent audit for payments
   (`docs/REBUILD_PLAN.md`'s stack table, "Matches audited-correct webhook signature verification
   code from Emergent").

## Scope (candidate, not final)

- **SDKs** — client libraries for whatever API surface this programme eventually defines; entirely
  downstream of the API's own design, not a first deliverable.
- **APIs** — the actual external-facing endpoints; scope determined by which capabilities
  Objective 2 identifies as safe to expose, likely starting with read-only, narrow, non-tenant-
  identifying capabilities (mirroring Government's own "public verification" candidate concept,
  `docs/GOVERNMENT_PROGRAMME_STRATEGY.md`) before any write capability is considered.
- **OAuth** — the likely mechanism for a third-party application acting on behalf of a LandVault
  tenant's own user (as opposed to a service-to-service API key acting as its own principal) — a
  distinct authorization flow from Objective 1's service-account model, not a replacement for it.
- **Webhooks** — see Objective 4.
- **Sandbox** — see Objective 3.
- **Developer Portal** — the human-facing surface for credential management, documentation, and
  usage analytics; likely the least architecturally novel item in this list (a dashboard over data
  the rest of this programme produces), and so likely sequenced last, not first.
- **API Marketplace** — a future capability allowing third parties to publish their own
  integrations for other LandVault participants to discover and use; the most speculative item in
  this list, named only because the governing review named it, with no further scoping
  recommended until the more foundational items above are resolved.

## Relationship to existing architecture

No change to Identity's existing `User`/authentication model is proposed — only an extension,
mirroring how every other extension in this platform's history (Tenant, Delegation, Parcel,
ParcelGeometry) has been additive to a frozen baseline, never a rewrite of it
(`docs/ARCHITECTURE_HANDBOOK.md` Part IX). Any API endpoint this programme eventually builds still
authorizes every request through the existing PDP/PEP/PIP engine — a public API surface changes
*what* is exposed and *how narrowly* it is scoped, never *how* authorization decisions are made.

## Approval Gate

No Developer Platform programme work has begun. This document names the new non-human-principal
and sandbox-isolation concerns this programme would introduce, and treats Developer Platform and
API Ecosystem as one planning exercise pending further scoping — it does not decide which
capability, if any, is safe to expose first. **Waiting for explicit direction before any Developer
Platform programme discovery begins.**
