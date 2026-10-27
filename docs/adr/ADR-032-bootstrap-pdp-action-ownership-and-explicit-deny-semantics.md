# ADR-032 — Bootstrap PDP Action Ownership and Explicit-Deny Semantics

**Status:** **ACCEPTED — 2026-10-27, on explicit Governance Authority ratification. IN FORCE.**

**Date:** 2026-10-27.

**References:** `ADR-031` (Initial Supabase Identity Bootstrap and First-Tenant Provisioning — qualified by this ADR, not amended); `ADR-004` §2–§5 (PDP/PEP, single authorization path); `LV-000` Article X §3.

**Related non-operative drafting context:** `GD-016` implementation-authorization draft — **PROPOSED / NOT AUTHORIZED / NOT IN FORCE**. `GD-016` is not current governing authority, grants no implementation permission, and is cited here only because its remediation depends on this ADR's resolution — not as a repository authority this ADR relies on or ratifies.

**Document control:** This is the complete, self-contained ratified text of ADR-032, accepted by the Governance Authority on 27 October 2026. It narrowly qualifies ADR-031's two bootstrap-policy fall-through clauses only. No section below depends on companion conversation material or an earlier draft.

## Ratification Record

Ratified by the Governance Authority for AquaSavannah LandVault on 27 October 2026.

The Governance Authority expressly adopted:

"ADR-032 — Bootstrap PDP Action Ownership and Explicit-Deny Semantics"

as:

"ADR-032 — RATIFIED / ACCEPTED — 27 October 2026 — IN FORCE."

Ratification accepts:

- action ownership for `identity.bootstrap_preflight`;
- action ownership for `identity.bootstrap_first_tenant`;
- explicit DENY for matching-action condition failure;
- defer/`None` only for unrelated actions;
- priorities 15 and 16;
- preservation of existing priorities 10, 11, 20, 30 and 40;
- preservation of `platform.super_admin` for unrelated actions;
- continued bootstrap exclusion of `super_admin`;
- role allowlist `{compliance_officer, surveyor_general}`;
- the narrow qualification of ADR-031 only.

**This ratification is architecture clarification acceptance only. It does not authorize implementation.**

## Context

The PDP (`backend/app/kernel/authorization/pdp.py`) is first-explicit-decision-wins: it evaluates registered policies in ascending priority order and returns the first non-`None` result; a policy returning `None` means "defer," and evaluation continues to the next policy. Among the currently registered default policies, `platform.super_admin` (priority 20) returns PERMIT for **any** action whenever the calling principal holds the `super_admin` role — it does not inspect which action is being authorized.

`ADR-031` writes both of its bootstrap policies — `identity.bootstrap_preflight` and `identity.bootstrap_first_tenant` — as ordinary deferring policies: "PERMIT iff `<conditions>`; otherwise defer (`None`) → PDP default-deny." A `super_admin`-role principal invoking either bootstrap action fails that policy's own required condition (`ctx.roles == ()`), so under this written semantics the policy returns `None` rather than an explicit decision. Because `None` means defer, evaluation continues past it. If the bootstrap policy sits at a priority after 20, `platform.super_admin` has already matched and permitted before the bootstrap policy is even reached. If the bootstrap policy sits at a priority before 20 and still returns `None` on failure, evaluation falls through to `platform.super_admin` all the same, which permits unconditionally. Either way, the result is PERMIT for a `super_admin` principal — directly contradicting `ADR-031`'s own separate, explicit requirement that `super_admin` be excluded from bootstrap "at the earliest possible point." Moving a still-deferring bootstrap policy to a different priority cannot close this gap by itself: priority only decides which policy is asked first, not what happens after a policy that matched the action declines to decide. Only replacing the deferring failure branch with an explicit DENY — which stops the evaluation outright under "first explicit decision wins" — prevents the walk from ever reaching `platform.super_admin` for these two actions.

## Problem

Make `ADR-031`'s already-binding bootstrap role restrictions and fail-closed guarantees actually effective against the PDP as it exists today, without redesigning the bootstrap mechanism and without altering any existing policy's behavior for any action other than the two named here.

## Decision

`identity.bootstrap_preflight` and `identity.bootstrap_first_tenant` are defined as **action-owning** policies:

**For `identity.bootstrap_preflight`:**
- **A.** If `action != "identity.bootstrap_preflight"`: return `None` (no-op for every other action — unchanged PDP behavior for everything else).
- **B.** If `action == "identity.bootstrap_preflight"` and every `ADR-031` condition holds: return `Decision.permit(...)`.
- **C.** If `action == "identity.bootstrap_preflight"` and any required condition fails: return `Decision.deny(...)` **explicitly** — never `None`.

**For `identity.bootstrap_first_tenant`:** the identical A/B/C structure, substituting its own action name and its own `ADR-031` conditions.

Branch C applies to every condition failure `ADR-031` §"Stage 1/Stage 2 policy" already names, including but not limited to: anonymous context; an effective tenant already present; an effective role already present; a `super_admin` principal; a `general_user` principal; any role outside `{compliance_officer, surveyor_general}`; a missing or incorrect `invocation_channel`; a missing or false `preflight_permitted` fact; a missing or false `platform_empty` fact; an invalid requested role.

## Precedence

Both policies register at:

- `identity.bootstrap_preflight` — priority **15**
- `identity.bootstrap_first_tenant` — priority **16**

placed after `platform.tenant_isolation` (10) and `platform.country_isolation` (11 — both already no-ops for bootstrap's resource shape, since bootstrap's `resource` carries no `tenant_id`/`country` key) and strictly before `platform.super_admin` (20). No existing priority (10, 11, 20, 30, 40) is modified. `platform.super_admin` itself is not modified and is not narrowed for any action other than these two — it continues to permit `super_admin` unconditionally for every action this ADR does not name.

Existing policies remain exactly:

- `platform.tenant_isolation` = 10
- `platform.country_isolation` = 11
- `platform.super_admin` = 20
- `platform.anonymous_public` = 30
- `identity.self` = 40

No existing policy is modified by this ADR.

## Scope of qualification

This ADR qualifies **exactly** `ADR-031`'s two instances of the phrase "otherwise: defer (`None`) → PDP default-deny" — one for each of `identity.bootstrap_preflight` and `identity.bootstrap_first_tenant` — and nothing else in `ADR-031`'s text. For those two actions only, the binding replacement is: **"matching action + failed required condition → explicit DENY."** No other sentence, table, invariant, or requirement in `ADR-031` is altered. `ADR-031`'s historical file is not edited. Every other `ADR-031` requirement remains in force unchanged.

## Explicitly unchanged

The two-stage PDP design; trusted CLI-only invocation (`env.invocation_channel == "bootstrap_cli"`); no HTTP route; the role allowlist `{compliance_officer, surveyor_general}`; the `super_admin` exclusion (now actually enforced, not merely stated); the ten-step bootstrap sequence; PERMIT-before-override ordering; the transaction-local RLS override; the `EXCLUSIVE` lock on `tenants`; the authoritative `platform_empty` fact; audit semantics (both the independent/eager class and the transaction-coupled class); the staged-audit call-site requirement; the actor-attribution boundary; the migration position ("no migration currently expected"); the review schedule; and `ADR-031`'s own implementation non-authorization. None of these are touched by this ADR.

## Validation examples

| Scenario | `action` matches a bootstrap action? | Bootstrap policy's own verdict | Does evaluation reach `platform.super_admin` (priority 20)? | Final decision |
|---|---|---|---|---|
| Stage 1: authenticated, `ctx.tenant_id is None`, `ctx.roles == ()`, requested role in `{compliance_officer, surveyor_general}`, `env.invocation_channel == "bootstrap_cli"` | Yes | PERMIT (branch B) | No (stopped) | **PERMIT** |
| `super_admin` role + `identity.bootstrap_preflight` | Yes | explicit DENY (branch C — `ctx.roles != ()`) | No (stopped at priority 15, before 20) | **explicit DENY** |
| `general_user` role + `identity.bootstrap_preflight` | Yes | explicit DENY (branch C) | No | **explicit DENY** |
| Correct role/context, wrong/missing `invocation_channel` | Yes | explicit DENY (branch C) | No | **explicit DENY** |
| Stage 2: action exactly `identity.bootstrap_first_tenant`; authenticated context; `ctx.tenant_id is None`; `ctx.roles == ()`; `preflight_permitted is True`; `platform_empty is True`; requested role exactly `compliance_officer` or `surveyor_general` | Yes | PERMIT (branch B) | No | **PERMIT** |
| Stage 2: `platform_empty is False` (all other conditions satisfied) | Yes | explicit DENY (branch C) | No | **explicit DENY** |
| Unrelated action (e.g. `registry.parcel.read`) + `super_admin` role | No | `None` (branch A — not this action) | Yes | **PERMIT** via `platform.super_admin`, unchanged |
| Unrelated action + ordinary authenticated user | No | `None` (branch A) | Falls through to whichever existing policy already governs that action | **unchanged from today** |

## Governance relationship

This ADR explicitly names and narrowly qualifies `ADR-031`; it does not edit `ADR-031`'s historical text. It resolves exactly one discovered PDP-composition inconsistency between `ADR-031`'s written bootstrap-policy semantics and the already-registered `platform.super_admin` default policy. It does not authorize implementation of anything — not the bootstrap command, not either policy function, not this ADR's own corrected pseudocode. It does not ratify `GD-016`, which remains **PROPOSED / NOT AUTHORIZED / NOT IN FORCE** and requires its own remediation (action-owning/explicit-DENY semantics and priorities 15/16) and independent re-review before any ratification is considered. It does not modify `ADR-009` or `ADR-012`. It does not modify any existing kernel default policy (`platform.tenant_isolation`, `platform.country_isolation`, `platform.super_admin`, `platform.anonymous_public`, `identity.self`) — their code, priority, and behavior are unchanged. It does not authorize any source-code change; it is architecture clarification only.

## Consequences

`ADR-031`'s `super_admin`-exclusion guarantee becomes actually true under the real PDP registry, not merely asserted in prose. `GD-016`, once remediated to reflect action-owning/explicit-DENY semantics and the 15/16 priorities, can proceed through independent review without carrying this latent defect forward into implementation. No change occurs to any currently-shipped, in-force policy's behavior for any action this ADR does not name.

## Explicit non-authorizations

This ADR does not authorize: implementation of either bootstrap policy; implementation of the `ADR-031` bootstrap command; modification of `platform.super_admin`; modification of any other existing default policy; any change to priorities 10, 11, 20, 30, or 40; any database change; any migration change; an HTTP bootstrap capability; production bootstrap execution; user creation; ratification of `GD-016`; or implementation of `GD-016`.
