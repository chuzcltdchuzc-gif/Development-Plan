# ADR-031 — Initial Supabase Identity Bootstrap and First-Tenant Provisioning

**Status:** **ACCEPTED — 2026-10-22, on explicit Governance Authority ratification. IN FORCE.**

**Date:** 2026-10-22

**References:** `ADR-004` (Authentication & Authorisation Model); `ADR-009` (B1 Platform Freeze); `ADR-010` (Tenant/Organization Aggregate); `ADR-012` (B2 Platform Freeze); `ADR-025` (Supabase Platform Baseline); `ADR-029` (Audit Transaction Semantics and Outcome Integrity); `ADR-030` (Audit Chain Concurrency, Ordering, and Linearization); `GD-009` (Audit Transaction Semantics Implementation Authorization); `GD-010` (Audit DAG Verifier Implementation Authorization); `GD-011` (GD-009 Batch 1 Resumption Authorization); `LV-000` Article VIII §§1, 3, 4; Article IX §§1–4; Article X §3.

**Document control:** This is the complete, self-contained ratified text of ADR-031, consolidated from a multi-pass Governance review and accepted by the Governance Authority on 22 October 2026. No section below defers to an earlier draft; every section is stated in full.

## Ratification Record

Ratified by the Governance Authority for AquaSavannah LandVault on 22 October 2026.

The Governance Authority expressly adopted:

"ADR-031 — Initial Supabase Identity Bootstrap and First-Tenant Provisioning"

as:

"ADR-031 — RATIFIED / ACCEPTED — 22 October 2026 — IN FORCE."

Ratification accepts the architecture stated in this ADR, including its two-stage PDP authorization model, controlled administrative RLS override, serialized first-tenant bootstrap invariant, role restrictions, audit semantics, actor-attribution boundary, review obligations, and relationships to the governing ADRs and Governance Decisions.

This ratification is architecture acceptance only.

It does not authorize implementation, source-code modification, migration creation or execution, use of `audit_staged()` at new bootstrap call sites, user creation, production bootstrap execution, commit, push, pull request, or merge.

Implementation requires a separate, explicit Governance Decision.

---

## Context

`ADR-025` made Supabase Auth the production identity provider and explicitly left "how first-login provisioning changes under Supabase Auth" as undecided future implementation work. Independent architecture review confirms a genuine circular dependency on any freshly-provisioned deployment:

- A Supabase-verified JWT only becomes a usable LandVault `ExecutionContext` with effective tenant/role attributes if a matching `identity_users` row exists and is currently active (`context_hydration.py`).
- The only way to create that row for a Supabase subject is accepting an existing invitation (`AuthService.accept_invitation_supabase`), which itself requires an existing invitation.
- Creating an invitation (`AdminService.create_invitation`), and assigning any `GOVERNANCE_ROLES` role (`AdminService.assign_role`), both require an existing user already holding `super_admin`, `surveyor_general`, or `compliance_officer`.
- The one self-service path that bypasses this, `AuthService.register_local` (`/v1/auth/register`), is Keycloak-based — a retired identity target under `ADR-025` that the Supabase-authenticated frontend never calls — and even there, self-registration grants only `general_user` (rank 0 in `ROLE_RANK`), which is below `GOVERNANCE_ROLES` and below `Registry`'s `PARCEL_REGISTRANT_ROLES`.

A freshly migrated database therefore has no way, through any existing exposed capability, to reach a state where a human can do anything beyond signing in anonymously.

## Problem

Define a bootstrap mechanism that creates exactly one first tenant and its first privileged user, safely, exactly once, correctly against every other tenant-creating path (not merely against itself), without introducing a permanent public attack surface, without weakening the PDP/PEP/PIP model, without a second authorization path (`LV-000` Article X §3), and without activating a privileged database override before any authorization decision has been made for it (`LV-000` Article VIII §4).

## Decision

A **server-side-only, operator-invoked management command** (no new HTTP route) performs first-tenant-and-owner provisioning, traversing the existing PDP/PEP authorization path **twice** — once to authorize a minimal privileged read, once to authorize the mutation — never activating elevated database access ungated.

### The ten-step bootstrap sequence

1. **Verify** the operator-supplied Supabase access token through the governed verifier — the same `JwtVerifier` + `SupabaseJWKSProvider` the PEP already uses for every request — yielding a verified `(identity_subject, email)`.
2. **Construct and bind an `ExecutionContext`** from these verified claims only — exactly the context the existing hydration pipeline would already produce for this subject today if it hit any ordinary endpoint (`principal_id = identity_subject`, `email = email`; `tenant_id` and `roles` reflect whatever the hydrator currently resolves for this subject, per step 2 of "Decision," no parallel identity mechanism is introduced).
3. **Run bootstrap-preflight PDP authorization** — `enforce("identity.bootstrap_preflight", resource={"requested_role": role}, env={"invocation_channel": "bootstrap_cli"})` — before any transaction, any GUC, and any lock exist. This call already, unconditionally, independently audits its own outcome (see "PDP/PEP treatment," below).
4. **Only on PERMIT**, begin the privileged transaction-local bootstrap probe: open one transaction, connected as the ordinary `landvault_app` role (never the schema-owning role).
5. **Activate the transaction-local RLS override**: `set_config('app.is_super_admin', 'true', is_local := true)`.
6. **Acquire** `LOCK TABLE tenants IN EXCLUSIVE MODE`, as the first statement after override activation.
7. **Determine `platform_empty`**: `SELECT count(*) FROM tenants`, under the now-active override, inside the lock — this is the authoritative, race-free fresh-platform fact (see "Correcting 'unprovisioned' semantics," below).
8. **Run the final PDP action** — `enforce("identity.bootstrap_first_tenant", resource={"requested_role": role}, env={"preflight_permitted": True, "platform_empty": platform_empty})` — independently audited, via the same mechanism as step 3.
9. **Only on final PERMIT**, perform the Tenant/User/owner-FK mutation, and stage the two successful-mutation audit events into this same transaction.
10. **Commit or roll back.** The `EXCLUSIVE` lock and the `is_super_admin` GUC are both released automatically at transaction end, regardless of outcome.

Both PDP actions use the **existing** `authorize()`/`enforce()` architecture and the existing policy registry (`app.kernel.authorization.policies`) — no separate CLI authorization engine is introduced. **Default outcome is DENY** at both stages, by the PDP's own existing fail-closed default (no matching policy → `Decision.deny(...)`).

### Stage 1 policy — `identity.bootstrap_preflight`

Authorizes **only** the privileged read establishing `platform_empty` at step 7 — nothing else.

```
identity.bootstrap_preflight:
  PERMIT iff:
    action == "identity.bootstrap_preflight"
    AND ctx.is_authenticated
    AND ctx.tenant_id is None
    AND ctx.roles == ()
    AND env.get("invocation_channel") == "bootstrap_cli"
    AND resource.get("requested_role") in {"compliance_officer", "surveyor_general"}
  otherwise: defer (None) → PDP default-deny
```

**Correcting "unprovisioned" semantics (binding on this condition's meaning):** `ctx.tenant_id is None AND ctx.roles == ()` must be read, precisely, as: **"the verified subject currently has no effective hydrated LandVault tenant or role context."** This condition, **by itself, does not prove the subject has never previously existed in LandVault** — the same empty-attrs shape can also result from an existing but currently suspended/inactive `identity_users` row, or from a tenant that is itself suspended/archived (`context_hydration.py`'s documented fail-closed behavior on either condition). It is a **fail-closed authorization-context condition**, not a historical-non-existence proof, and this ADR does not weaken it to claim otherwise — it still correctly excludes any subject with *currently* effective roles/tenant from reaching the preflight probe at all, which is exactly the narrow gate this stage needs. **The authoritative fresh-platform condition is the later, separate fact**: `platform_empty == true`, established at step 7, under the `EXCLUSIVE` lock on `tenants`, inside the serialized window — that is what this ADR actually relies on to prove the platform is genuinely uninitialized, not the shape of `ctx`.

This policy must not, and under this design cannot, authorize Tenant creation, User creation, role assignment, owner assignment, or any state mutation — it grants only the right to proceed to the read probe at step 7. `super_admin` is rejected here already, at the earliest possible point, not deferred to Stage 2.

### Stage 2 policy — `identity.bootstrap_first_tenant`

Authorizes only the specific initial-provisioning mutation.

```
identity.bootstrap_first_tenant:
  PERMIT iff:
    action == "identity.bootstrap_first_tenant"
    AND ctx.is_authenticated
    AND ctx.tenant_id is None AND ctx.roles == ()     # same no-effective-local-context condition, re-asserted
    AND env.get("preflight_permitted") is True        # Stage 1 already permitted this exact flow
    AND env.get("platform_empty") is True              # the authoritative fresh-platform fact (step 7)
    AND resource.get("requested_role") in {"compliance_officer", "surveyor_general"}
  otherwise: defer (None) → PDP default-deny
```

As with Stage 1, `ctx.tenant_id is None AND ctx.roles == ()` here means only "no effective hydrated context at the moment of this check" — it is **`platform_empty == true`, established inside the serialized `EXCLUSIVE`-locked window, that proves the initial-platform prerequisite**, not the context shape. "No tenant committed before the serialized empty-platform check" is exactly what `platform_empty` establishes; it is not a separate condition.

## Security invariants

- No public, unauthenticated, or permanently-reachable HTTP endpoint is introduced anywhere by this ADR.
- No default credentials and no hardcoded email/principal ID are embedded in this mechanism.
- The granted role is operator-supplied at invocation time and constrained by both PDP policies to `{compliance_officer, surveyor_general}` — never caller-controlled beyond that set, never read from a request body (there is no HTTP request), never defaulted to `super_admin`.
- The command is usable only against a genuinely empty `tenants` table, proven under an `EXCLUSIVE` lock, not merely asserted.
- Server-side only; requires the same infrastructure-access trust tier this system already relies on for running Alembic migrations.
- Fail-closed throughout: both PDP stages default-deny; any failure before the final commit leaves the platform in its prior state, safely re-attemptable; any attempt after a successful prior run fails closed at Stage 2's `platform_empty` condition.
- No Supabase service-role/admin-API credential is required or used by this command — it only verifies an already-issued token, the same operation the PEP already performs on every request.
- The privileged database override (`app.is_super_admin`) is never activated except strictly after Stage 1 PERMIT, is transaction-local, and is self-resetting.

## Administrative RLS override

`app.is_super_admin = 'true'`, set via `set_config(..., is_local := true)` at step 5, is a **break-glass/administrative override path under `LV-000` Article VIII §4**, governed accordingly, not described as a mere technical RLS detail:

- **Narrow**: scoped to exactly this transaction, exactly this command, exactly the step-7 read and the step-9 writes. It grants nothing to any other code path, request, or time outside this one transaction's lifetime.
- **Gated by its own authorization**: activated only after `identity.bootstrap_preflight` PERMIT (step 4→5), never before any PDP decision exists for it — this is the specific gap closed relative to earlier drafts of this ADR.
- **Transaction-local and self-resetting**: `is_local := true` means Postgres clears the GUC automatically at transaction end — no persistent elevated state survives the command.
- **Not reachable through any HTTP route**: no router mounts `identity.bootstrap_preflight` or `identity.bootstrap_first_tenant`; nothing in `app/main.py` exposes either to an HTTP caller. (The underlying GUC *mechanism* itself is not new or CLI-exclusive — see "HTTP/GUC clarification," below — only the *bootstrap capability* is non-HTTP.)
- **Not settable by user-controlled input**: the command hardcodes the literal `'true'` value it sets, exactly as `build_production_context_hydrator`'s existing one-off super-admin bypass already does today (`ADR-009` §10) — not a new pattern.
- **Used only for the global-empty check and the writes required for initial provisioning** — nothing broader.
- **Audited as an administrative override, explicitly and independently** — see "Audit semantics," below.
- **Reviewed on a schedule** — see "Review schedule," below.

This does not broaden ordinary runtime authorization in any way: `landvault_app`'s grants are unchanged, the RLS policies on `tenants`/`identity_users` are unchanged, and no other code path gains access to this override.

## PDP/PEP treatment

Both bootstrap PDP actions are invoked through the **existing, unmodified** `app.kernel.authorization.pep.enforce()` function, read directly:

```python
async def enforce(action, *, resource=None, env=None) -> Decision:
    """Programmatic PDP check. Raises 403 on DENY; audits both outcomes."""
    decision = authorize(action, resource=resource, env=env)
    await audit(
        action="authz." + ("permit" if decision.permitted else "deny"),
        resource_type=(resource or {}).get("resource_type", "unknown"),
        resource_id=(resource or {}).get("resource_id"),
        decision=decision.effect.value,
        payload={"action": action, "reason": decision.reason, "policy_id": decision.policy_id},
    )
    if not decision.permitted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=decision.reason)
    return decision
```

`enforce()` **already, unconditionally, independently audits both outcomes**, via the plain `audit()` call (the eager/independent store). This is preserved **unchanged**; no duplicate PDP-decision record is invented for either stage. This is **sufficient, on its own**, to record *that* each PDP decision was made, by which policy, and why — for both `identity.bootstrap_preflight` and `identity.bootstrap_first_tenant`.

`enforce()` raising `HTTPException` on DENY functions correctly outside an HTTP request context: `HTTPException` is an ordinary Python exception class when not handled by FastAPI's own exception machinery; the bootstrap command catches it directly and reports a clean failure to the operator, with no HTTP semantics implied or required.

**One additional, narrowly-scoped record is still required — not for either PDP decision, but for the override's actual use** (see "Audit semantics," below) — because an `authz.permit` entry for `identity.bootstrap_preflight` records an *authorization* fact (the PDP decided this flow may proceed), not the *operational* fact that `app.is_super_admin` was actually set and a privileged read actually occurred under it, which `LV-000` Article VIII §4 separately requires be auditable as override *usage*. In this design the two facts are 1:1 (Stage 1 PERMIT always leads directly to override activation), so the records will always co-occur — but they are recorded for different reasons and are not collapsed into one.

## Cross-path concurrency and lock ordering

**Required ordering, exact, not illustrative:**

```
PRE-FLIGHT PDP PERMIT (step 3)
→ begin bootstrap transaction (step 4)
→ set transaction-local RLS override (step 5)
→ acquire EXCLUSIVE lock on tenants (step 6)
→ empty-platform check (step 7)
→ final bootstrap PDP (step 8)
→ mutation on PERMIT (step 9)
→ commit/rollback (step 10)
```

`LOCK TABLE tenants IN EXCLUSIVE MODE` is acquired **before** the serialized empty-platform check and remains held until transaction completion. `EXCLUSIVE` conflicts with `ROW EXCLUSIVE` (the mode any ordinary `INSERT` takes), so any concurrent attempt to insert into `tenants` — from `register_local`, from any future tenant-creation path, or from a second concurrent bootstrap invocation — blocks until this transaction ends, regardless of whether that other writer cooperates with or even knows about this lock. This requires **no modification to `register_local`** and therefore **no amendment to the frozen B1/B2 Identity behavior** `ADR-009`/`ADR-012` describe. `EXCLUSIVE` (not the stronger `ACCESS EXCLUSIVE`) is the deliberate minimum sufficient mode — it still permits concurrent plain `SELECT` during bootstrap's brief transaction.

**Race A — bootstrap obtains the lock first**: bootstrap observes an empty state at step 7, receives final PDP PERMIT at step 8, creates the initial tenant, and commits. A concurrent normal tenant creator blocks on its own `INSERT` until bootstrap's transaction ends, then proceeds normally to create a later tenant — **bootstrap does not permanently prohibit later legitimate tenant creation.**

**Race B — another tenant creator commits first**: that creator commits before bootstrap acquires the lock. Bootstrap then acquires the lock, observes a non-empty platform at step 7, and Stage 2's `platform_empty` condition is false — DENY, fail-closed, no mutation.

**If implementation reality later proves a different ordering is required for safe transaction semantics, implementation must STOP and return to Governance.** No improvisation on this ordering is authorized by this ADR.

## Audit semantics

**The fact that a privileged administrative override was requested, permitted or denied, activated, or used is not itself a successful-mutation event**, and must not be staged into the mutation transaction — it must survive even if the later Tenant/User mutation subsequently rolls back.

**A. Independent/eager durable** (existing `EagerPostgresAuditStore` path, via `audit()`, unchanged mechanism):
- `authz.permit` / `authz.deny` for `identity.bootstrap_preflight` (via `enforce()`, step 3).
- `identity.bootstrap.rls_override_used` — new, narrowly-scoped, recorded immediately after step 5 (override activation), independently committed. Establishes: the authenticated Supabase subject; that the bootstrap mechanism is what is exercising it; the action being supported (`identity.bootstrap_first_tenant`, pending); that the transaction-local `app.is_super_admin` override was activated; its purpose (initial-platform bootstrap probe/provisioning). No secret values.
- `authz.permit` / `authz.deny` for `identity.bootstrap_first_tenant` (via `enforce()`, step 8).
- Token-verification rejection, where audit-eligible (a malformed/unverifiable token that never reaches step 2 at all may have nothing to attribute an entry to — handled as an ordinary, non-attributable failure, not silently dropped if any verifiable claim exists to attribute it to).
- Any other bootstrap denial or operational failure.

**B. Transaction-coupled successful mutation** (staged per `ADR-029`, commits or rolls back with the mutation — **only** these two):
- `identity.tenant.bootstrapped` — `resource_type="tenant"`, `resource_id=<new tenant id>`, payload `{"via": "bootstrap"}`.
- `identity.user.registered` — `resource_type="user"`, `resource_id=<new user id>`, payload `{"country": <country>, "role": <operator-chosen role>, "via": "bootstrap"}`.

Nothing else belongs in category B. No password, access token, service-role credential, or database credential appears in any payload in either category.

**This ADR does not itself authorize writing to `audit_staged()`/`AuditStore.append_staged()` from bootstrap's two category-B call sites.** That mechanism already exists and is already in force on current `main` — see "GD-009/GD-010/GD-011 status," below — but its own docstring states it must be "called explicitly, by name, at an authorized call site only," and today's authorized call sites remain exactly `EvidenceActorAttributionService.record_attribution`/`correct_attribution`. A future, separate implementation-authorizing Governance Decision must explicitly name `identity.tenant.bootstrapped` and bootstrap's `identity.user.registered` as additionally-authorized call sites, on the same precedent `GD-009`/`GD-011` already set — this ADR names the requirement; it does not extend the list itself.

## Actor attribution

**The system proves only which verified Supabase subject's credential authorized the operation — it does not, and cannot, independently prove the physical identity of the person controlling the terminal that invoked the command.**

- **Audit `principal_id`, on every event this command produces, is the verified Supabase subject whose credential authorized the bootstrap** — an accurate statement of what was cryptographically verified, nothing more, consistent with (not a new convention beyond) `_provision_user_from_invitation`'s existing pattern of sourcing `principal_id` from the ambient, just-verified identity.
- `resource_id` on the two success events is the resulting internal LandVault `Tenant`/`User` id.
- Payloads carry `"via": "bootstrap"` (mirroring `_provision_user_from_invitation`'s existing `"via": invitation.invitation_id` field) and the administrative-override evidence described above — distinguishing operator-invoked, infrastructure-level provisioning from self-service invitation acceptance, in the audit record itself.
- **LandVault does not independently verify that the human running the CLI is the same human who controls the Supabase account whose token was supplied.** No claim to the contrary is made anywhere in this ADR.
- **Proxy bootstrap — one operator using a different subject's token to bootstrap on that subject's behalf — remains operationally prohibited** by this ADR's own procedure, as a constraint on how the command is meant to be used, not as a property the software technically enforces or proves.
- **A future requirement for one operator to provision a genuinely different person's identity** requires its own, separate dual-actor attribution architecture and remains explicitly outside this ADR.
- No password, token, or key is ever recorded.

## First-user role

Constrained to exactly `{compliance_officer, surveyor_general}`, enforced by **both** PDP policies — the preflight policy rejects an impermissible role before any privileged read occurs; the final policy re-asserts the same constraint before mutation. No free-form role input is accepted at either stage.

| Role | Rank | In `GOVERNANCE_ROLES`? | Can invite/assign afterward? | Suitable as bootstrap default? |
|---|---|---|---|---|
| `general_user` | 0 | No | No | **No** — reproduces the exact circularity this ADR closes |
| `compliance_officer` | 40 | Yes | Yes (up to rank 40) | **Yes** |
| `surveyor_general` | 40 | Yes | Yes (up to rank 40) | **Yes** |
| `super_admin` | 100 | Yes | Yes, unrestricted | **No, excluded by design** — platform-wide, cross-tenant authority must never be an implicit side effect of bootstrapping one tenant |

Nothing in the current role definitions distinguishes which of `compliance_officer`/`surveyor_general` is the more generically appropriate "tenant administrator" — both are domain-flavored names at the same rank — so this ADR requires the operator to choose explicitly, at invocation time, between exactly these two, rather than asserting a false universal preference. `super_admin` elevation for the bootstrapped user, if ever needed, remains a separate, subsequent, independently authorized `assign_role` action.

## Token handling

The Supabase access token **must never appear as an ordinary command-line argument**. The command reads it from **stdin only**, or an equivalent protected file descriptor passed explicitly and closed immediately after read. It must never appear in: shell history, `ps`/process-list output, application logs, any audit record (including the override-usage and PDP-decision records above), any raised exception's text, or Git. No password of any kind is required by this command — it verifies an already-issued token, it never authenticates a password itself.

## Supabase interaction

`SupabaseJWKSProvider` (`backend/app/contexts/identity/adapters/supabase.py`) is documented as never proxying Supabase Auth — "no register/login/refresh proxying." This command never calls Supabase's Admin API and never creates a Supabase user itself. The operator creates/invites the Supabase identity through Supabase's own existing mechanisms first, entirely outside this command; this command only verifies an already-issued token.

## Failure / retry / idempotency semantics

- **Preflight DENY**: no privileged RLS override is ever activated (step 5 is never reached). The independent `authz.deny` record for `identity.bootstrap_preflight` is durable.
- **Override activated, later final PDP DENY**: the transaction rolls back with no domain mutation. The independent `identity.bootstrap.rls_override_used` record and the independent `authz.deny` record for `identity.bootstrap_first_tenant` both remain durable, unaffected by the rollback.
- **Failure before domain commit** (e.g. a DB error during the mutation itself, after final PERMIT): the Tenant/User/owner-FK changes roll back, and the transaction-coupled successful-mutation audit events roll back with them, by construction under `ADR-029`'s invariant. The independent override/PDP-decision records from earlier in the same attempt remain durable regardless.
- **Successful bootstrap**: Tenant, User, owner-FK, and the two successful-mutation audit entries commit together in the one transaction; the independent preflight/override/final-PDP records from the same attempt are already durable from before the transaction's own commit point.
- **Retry after a failed or denied bootstrap**: safe, provided the platform remains genuinely uninitialized — a fresh attempt repeats the full ten-step sequence.
- **Retry after a successful bootstrap**: fails closed at Stage 2's `platform_empty` condition (and, in most retry scenarios, likely already at Stage 1 once a real `identity_users` row exists for the same subject) — never a silent no-op, and never a second tenant.

## Review schedule

No existing repository-governed cadence for privileged/administrative-override review was found to apply to this kind of override. Per `LV-000` Article VIII §4's requirement that override paths be "reviewed on a schedule," this ADR specifies the following as its own minimum:

- **Every successful bootstrap invocation** receives a **post-event privileged-access review** — an explicit, recorded governance review of that specific override's exercise, triggered by the event itself.
- **All bootstrap override events — including denied and failed attempts** — are included in a **regular quarterly privileged-access review**, alongside any other administrative-override activity this platform accumulates.

Establishing this requirement and its cadence is this ADR's own decision; conducting the reviews themselves is an operational/governance process, not application code, and is not restricted by this ADR's non-authorization clauses.

## HTTP/GUC clarification

**The `app.is_super_admin` GUC mechanism itself is not new, and is not exclusive to CLI bootstrap.** It is already used today, via ordinary HTTP requests, in two existing cases (`app.kernel.uow.get_db_session`, `ADR-009` §10): anonymous registration/login requests, and authenticated requests from a principal already holding `super_admin`. **What this ADR introduces no HTTP access to is the *bootstrap capability* specifically** — no new route exists, and no HTTP caller of any kind can reach `identity.bootstrap_preflight` or `identity.bootstrap_first_tenant`, because nothing in `app/main.py`'s router mounting exposes either action. The GUC itself remains exactly as general-purpose, and already exactly as HTTP-reachable for its two existing, unrelated use cases, as it was before this ADR.

## Database authority (RLS)

`tenants` carries `FORCE ROW LEVEL SECURITY`, with policy `id = current_setting('app.tenant_id', true) OR current_setting('app.is_super_admin', true) = 'true'` (migration `0005`, verified directly against the actual migration source). `landvault_app` holds `SELECT, INSERT, UPDATE` on `tenants` (no `DELETE`, consistent with the table's archival-not-deletion convention). With neither GUC set, `landvault_app` would see **zero rows regardless of the table's true contents** — a false-empty result, which is precisely why step 7's reliability depends on step 5 having already activated the override.

**Evaluated options for this authority:**

- **A — Ordinary `landvault_app` connection, with the existing `app.is_super_admin = 'true'` GUC set for this transaction.** Not a new or novel RLS bypass — the **same mechanism `register_local`'s anonymous-registration path already uses today**, for the identical reason (a caller with nothing yet to scope to). `landvault_app`'s existing grants on `tenants` and `identity_users` are already sufficient; no new grant is required. **Selected.**
- **B — `MIGRATIONS_DATABASE_URL` / the schema-owning role.** Rejected: that role exists solely for DDL (`ADR-009` §6 — "the owning role is never used at runtime... because table ownership bypasses `GRANT`/`REVOKE` and RLS entirely"). Using it here would be a least-privilege regression this design has no reason to introduce.
- **C — A dedicated new bootstrap database role.** Rejected: adds a new credential and grant surface for a problem Option A already solves with zero new state.

The security consequence of the selected option: bootstrap's elevated visibility is scoped to exactly the same escape hatch, with exactly the same blast radius, `register_local` already exercises in production today — this ADR adds no new category of database privilege, only a second, narrowly-defined, PDP-gated caller of an existing one.

## Relationship to governing ADRs and Governance Decisions

| ADR / GD | Relationship |
|---|---|
| `ADR-004` §2–§5 (PDP/PEP/PIP, single auth path, hierarchy check, rate limiting) | **Unchanged**, and now exercised twice per bootstrap attempt, exactly as every other action already traverses it. The hierarchy check still governs every role grant this command makes. |
| `ADR-009` (B1 freeze — `backend/app/kernel/`, `backend/app/contexts/identity/`, migrations `0001`–`0003`) | **Not amended.** No change to anything §1–19 describes. The two new PDP policy-registry entries are additions of the kind `ADR-009` §2 already names as available to B2+; the database-authority mechanism and the migration-free table lock are both exercised exactly as already frozen. |
| `ADR-010` (Tenant/Organization aggregate) | **Not amended.** Bootstrap creates a `Tenant` via the exact lifecycle/FK shape `ADR-010`/`register_local` already establish — `ACTIVE` status, `owner_user_id` set via the same tenant→user→owner-FK three-step pattern. No new tenant state or transition is introduced. |
| `ADR-012` (B2 freeze — tenant provisioning/invitations) | **`ADR-031` is the later ADR `ADR-012` itself requires for any change touching this domain, and this is exactly such a change: it narrowly amends/supplements `ADR-012`'s frozen provisioning surface by adding one initial-platform bootstrap entry point, through this later ADR — not a retroactive edit of `ADR-012`'s own historical text.** Existing `register_local`, invitation, tenant-lifecycle, delegation, and role-assignment paths remain unchanged in code, contract, and behavior. |
| `ADR-025` | **Fulfilled, not amended** — this ADR is the deferred "first-login provisioning under Supabase Auth" work `ADR-025` itself named. |
| `ADR-029` (Audit Transaction Semantics) | **Not amended; binding.** See "Audit semantics" above for the exact class split this ADR complies with. |
| `ADR-030` (Audit Chain Concurrency) | **Not amended; unaffected.** Bootstrap's audit entries join the same global hash-linked DAG, under the same six verifier invariants, as every other entry. `ADR-030`'s own rejection of locking on the *audit chain's write path* (`prev_hash` contention, platform-wide, every request) is a distinct question from this ADR's `LOCK TABLE tenants` (a narrow, one-time, non-hot-path *domain* invariant on the `Tenant` table specifically) — the two are not in tension. |
| `GD-009` / `GD-010` / `GD-011` status | **`audit_staged()`/`AuditStore.append_staged()` already exist on current `main`**, under the authorization chain `ADR-029 → GD-009 → ADR-030 → GD-010 → GD-011`. `GD-011` (**Accepted, In Force**) already lifted `GD-009` §11's concurrency-related execution suspension, once `ADR-030`'s DAG topology was accepted and `GD-010`'s DAG-aware verifier was implemented and merged. **GD-009 Batch 1 resumption is not pending; nothing about it is currently suspended.** This status is **not broadened by implication**: `audit_staged()`'s own docstring restricts it to its currently-named call sites (`EvidenceActorAttributionService.record_attribution`/`correct_attribution`) only — see "Audit semantics" above for bootstrap's own, separate, future authorization requirement. |

**Frozen-scope clarification**: existing B1/B2 Identity code paths need not be modified by this ADR — but `ADR-031` **does extend** the Identity bounded context itself, with a new, explicitly governed bootstrap capability (two new PDP policies, a new application-layer command). "No modification required" describes the existing paths' own code; it does not mean the bounded context's surface is unchanged. Implementation of this extension remains prohibited until separately authorized.

**Preserved as written, unchanged**: the full text of every ADR named above. This ADR edits nothing retroactively.

## Migration position

**No migration currently expected** — conditioned explicitly on the selected architecture, which uses only: the existing `tenants` table; existing grants; the existing transaction-local GUC mechanism; the existing PDP policy registry; the existing audit schema (both the eager store and, pending its own separate call-site authorization, the transaction-coupled store); and PostgreSQL's native table-locking capability. **If implementation reality requires any of the following** — a persistent bootstrap sentinel, a new database role, a new audit schema, a new database constraint, a new table, any new persistent bootstrap state, or any other new database object — **implementation must STOP and return to Governance before creating a migration.** This ADR does not pre-authorize any such migration.

## Operational procedure

1. Operator causes the intended first user's Supabase identity to exist (sign-up or Supabase-side invite), entirely outside this command.
2. Operator obtains that identity's access token through normal sign-in.
3. Operator runs the bootstrap command, supplying the token via stdin, the tenant name, and the intended role (`compliance_officer` or `surveyor_general`).
4. Command executes the full ten-step sequence described in "Decision" above.
5. Operator uses the resulting account to perform all further provisioning through the existing, unmodified invitation flow.
6. The invocation — successful, denied, or failed — enters the review schedule named above.

## Alternatives considered

- **A — Public self-registration creating the first tenant**: rejected. A permanent, unauthenticated endpoint minting the platform's first privileged account is a standing attack surface forever, not just at deploy time; even if time-limited, it still repeats `register_local`'s own `general_user`-only insufficiency unless redesigned, at which point it duplicates this ADR's own design with an unnecessary HTTP surface.
- **B — A one-time HTTP bootstrap endpoint**: rejected on the same attack-surface grounds as A, with the added complexity of needing its own disable-after-use mechanism, which is itself new state to secure correctly.
- **C — A server-side/operator CLI or management command**: the category selected, combined with D below.
- **D — Supabase Dashboard/Admin-created user, followed by controlled local provisioning**: the identity-creation half selected — the operator causes the Supabase identity to exist first, through Supabase's own mechanisms, and this command only ever verifies an already-issued token, consistent with `SupabaseJWKSProvider`'s existing, documented scope (never proxying Supabase Auth).
- **Selected: a hybrid of C and D** — a CLI/management command (no new HTTP route) that verifies an operator-pre-created Supabase identity and provisions it locally, gated by the existing PDP at two stages. This adds zero new network-reachable surface and reuses `accept_invitation_supabase`'s already-shipped trust model (trust an already-verified external identity; decide tenant/role server-side) rather than inventing a new one.

## Consequences

- A fresh deployment gains a real, PDP-governed path to its first usable account — not a bypass of this platform's authorization architecture, an instance of it.
- No new permanent attack surface is introduced; no HTTP route is added.
- No modification to any frozen B1/B2 Identity code path is required; the Identity context gains two new, explicitly governed PDP actions and one new application-layer command.
- The administrative RLS override is fully reconciled with `LV-000` Article VIII §4: narrow, transaction-local, self-resetting, gated by its own Stage 1 authorization before activation, independently and durably audited both as a decision and as a use, and subject to a named review cadence.
- Bootstrap's two successful-mutation audit events remain governed by `ADR-029` and require their own future, explicit call-site authorization before implementation — this ADR does not grant that itself, and does not broaden `GD-009`/`GD-011`'s existing authorization by implication.
- Actor-attribution claims are limited to exactly what is cryptographically provable — which verified subject's credential authorized the action — and do not claim physical-identity proof.
- Every subsequent user, after the bootstrapped founder, still goes through the existing, unmodified invitation flow.

## Explicit non-authorizations

This ADR does not authorize: implementation of the command or either PDP policy; a new HTTP route of any kind; a Supabase Admin API integration; a default or permitted role outside `{compliance_officer, surveyor_general}`; a new call to `audit_staged()`/`AuditStore.append_staged()` for bootstrap's two call sites; dual-actor bootstrap (an operator provisioning a different person's identity); any database migration beyond what "Migration position" explicitly treats as currently unneeded; conducting the named reviews via any new tooling this ADR does not itself describe; any change to `ADR-004`/`ADR-009`/`ADR-010`/`ADR-012`/`ADR-025`/`ADR-029`/`ADR-030`'s own text, or to `GD-009`/`GD-010`/`GD-011`'s own authorized call-site scope; use in a live production environment before its own test matrix — including a live test proving the `EXCLUSIVE` lock excludes a concurrent `register_local` insert, a test proving both PDP policies fail closed by default, and a test proving the override is never activated on a Stage 1 DENY — is complete and reviewed.
