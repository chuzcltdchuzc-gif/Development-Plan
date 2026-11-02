# GD-016 — ADR-031 Initial Supabase Identity Bootstrap Implementation Authorization

**Status:** **ACCEPTED — 28 October 2026, on explicit Governance Authority ratification. IN FORCE.**

**Date:** 2026-10-28

**This Decision implements `ADR-031` as qualified by `ADR-032`.**

**Operative authority:** Article XVI §2 — a later numbered decision explicitly authorizing implementation of `docs/adr/ADR-031-initial-supabase-identity-bootstrap-and-first-tenant-provisioning.md` (Accepted, 2026-10-22) as qualified by `docs/adr/ADR-032-bootstrap-pdp-action-ownership-and-explicit-deny-semantics.md` (Accepted, 2026-10-27). Does not amend `ADR-031`, `ADR-032`, `ADR-009`, `ADR-012`, `ADR-029`, `ADR-030`, `GD-009`, `GD-010`, or `GD-011`. Not proposed under Article XIV; does not amend the Constitution.

## Ratification Record

Ratified by the Governance Authority for AquaSavannah LandVault on 28 October 2026.

The Governance Authority expressly adopted the final, independently reviewed version of:

"GD-016 — ADR-031 Initial Supabase Identity Bootstrap Implementation Authorization"

as:

"GD-016 — RATIFIED / ACCEPTED — 28 October 2026 — IN FORCE."

Ratification:

- adopts this Decision as implementing `ADR-031` as qualified by `ADR-032`;
- accepts the complete final corrected operative text below, in full, including its baseline/drift rules, the eleven-path implementation/test allowlist, the CLI input contract, the verified-email contract, the verified-Supabase-subject actor-attribution rule, the standalone CLI composition root, the eager-audit requirements, the RLS override and lock ordering, the `audit_staged()` documentation authority, the Tenant → User → owner persistence order, all 52 mandatory tests, all 21 STOP conditions, and all explicit non-authorizations;
- does **not** itself authorize implementation to begin before this Decision's own governance-publication sequence (§13) has completed;
- does **not** authorize production bootstrap execution, any migration, any HTTP bootstrap route, or any Supabase Admin API use;
- preserves every STOP condition and every phase gate exactly as drafted, without collapsing, shortening, or pre-satisfying any of them.

This ratification supersedes any earlier ratification statement only to the extent necessary to make this final corrected text the authoritative ratified version.

## 1. Baseline

**GD-016 architecture-review / ratification baseline**: `origin/main` = `3ada9722d9b553750fb7f5b7ab8732b71844b67f`. This SHA identifies the repository state this Decision's architecture review and drafting were performed against — it is the ratification baseline, not a permanent implementation SHA, and it is superseded once this Decision itself is ratified, recorded, and merged (§13). `ADR-031`: ACCEPTED, IN FORCE. `ADR-032`: ACCEPTED, IN FORCE — qualifies exactly `ADR-031`'s two bootstrap-policy fall-through clauses to action-owning, explicit-DENY semantics at priorities 15 (`identity.bootstrap_preflight`) and 16 (`identity.bootstrap_first_tenant`), leaving every other `ADR-031` requirement and every existing kernel default policy (`platform.tenant_isolation`=10, `platform.country_isolation`=11, `platform.super_admin`=20, `platform.anonymous_public`=30, `identity.self`=40) unchanged.

Two distinct drift checks govern this Decision, corresponding to two different moments:

**(A) Pre-ratification drift.** If `origin/main` no longer equals `3ada9722d9b553750fb7f5b7ab8732b71844b67f` at the time Governance Authority ratification is sought, this Decision returns to Governance for revalidation against the new repository state before ratification proceeds — see STOP condition #1(A) in §10.

**(B) Post-publication drift.** Once this Decision is ratified and its own text is committed, pushed, reviewed, and merged to `main` (§13's publication sequence), implementation does **not** run against `3ada9722d9b553750fb7f5b7ab8732b71844b67f` — it runs against whatever `main` SHA exists immediately after that merge. The separate implementation branch/worktree authorization (§13) must pin that exact post-publication SHA explicitly, at the time it is granted. If that later pinned SHA moves before implementation actually begins, implementation must STOP and return to Governance — see STOP condition #1(B) in §10. Implementation is not required to run directly from `3ada9722d9b553750fb7f5b7ab8732b71844b67f` once this Decision's own ratified record has been merged — it runs from the later pinned SHA instead.

## 2. Purpose

Authorizes the bounded implementation package in §3 below, implementing `ADR-031` exactly as qualified by `ADR-032`, and nothing beyond that package.

## 3. Authorized implementation and test file allowlist

**Responsibility split (binding, unambiguous):** the CLI file owns the standalone runtime composition, token verification, verified-email validation, hydration/context construction and binding, bootstrap-policy registration, and invocation of the bootstrap service — it is the sole composition root. `bootstrap_service.py` owns only the authorized bootstrap transactional/domain orchestration (§9 steps 3–10): it receives an already-verified subject, an already-normalized email, and an already-bound `ExecutionContext` from the CLI file, and never itself verifies a token, validates an email, or constructs/binds a context — no second composition root exists anywhere in this package. `bootstrap_policies.py` owns only the two bootstrap policy functions and their registration helper; it contains no orchestration logic.

**Production files (four):**

| File | Action | Purpose | Governing clause | Touches frozen B1/B2 scope? | Executable behavior changes? |
|---|---|---|---|---|---|
| `backend/app/contexts/identity/application/bootstrap_service.py` | CREATE | Bootstrap transactional/domain orchestration only (§9 below, steps 3–10): both `enforce()` calls, the bootstrap-transaction GUC/lock sequence, the Tenant/User/owner mutation in the exact persistence order §9 step 9 specifies, with `user.roles` set to exactly `[requested_role]`, and the two staged audit calls. Does not verify tokens, validate email, or construct/bind the `ExecutionContext` — those belong to the CLI file. | §7, §9 of this Decision | Yes — new file inside `backend/app/contexts/identity/`, licensed by `ADR-031`'s own frozen-scope clarification | Yes — this is new orchestration logic |
| `backend/app/contexts/identity/authorization/bootstrap_policies.py` | CREATE | `identity.bootstrap_preflight` (priority 15) and `identity.bootstrap_first_tenant` (priority 16), each implementing `ADR-032`'s action-owning/explicit-DENY semantics exactly: unrelated action → `None`; matching action + every condition satisfied → PERMIT; matching action + any condition failed → explicit `Decision.deny(...)`. Exposes `register_bootstrap_policies()`, which calls the kernel's existing public `register_policy()` function. Contains no orchestration logic. | `ADR-032` §"Decision"/"Precedence" | Yes — new file, same licensing | Yes — two new policy functions |
| `backend/app/contexts/identity/cli/bootstrap_first_tenant.py` | CREATE | Sole operator entrypoint and composition root: implements the CLI contract (§4), token verification and verified-email validation (§5), hydration/`ExecutionContext` construction and binding (§6), bootstrap-policy registration, and invocation of `bootstrap_service`. Calls `register_bootstrap_policies()` itself; never imported by `app/main.py`. | §4, §5, §6 | Yes — new file, same licensing | Yes — new entrypoint |
| `backend/app/kernel/audit_postgres.py` | **MODIFY — docstring only** | Synchronize `audit_staged()`'s authorized-call-site documentation to additionally name this Decision's two new call sites, per §8 below. | §8 of this Decision | Yes — this file is inside the B1 freeze (`backend/app/kernel/`) | **No** — zero executable statements, function signatures, or audit semantics change; documentation text only |

**Test files (seven):**

| File | Action | Purpose | Governing clause | Touches frozen B1/B2 scope? | Executable production behavior changes? |
|---|---|---|---|---|---|
| `backend/tests/test_identity_bootstrap_policies.py` | CREATE | Hermetic policy tests — §11 tests 2–6, 13–18, 24, 48. | §11 | No | No — test code only |
| `backend/tests/test_identity_bootstrap_service.py` | CREATE | Hermetic orchestration tests — §11 tests 19, 20, 22, 25–28, 30 (hermetic half), 33, 34, 43. | §11 | No | No — test code only |
| `backend/tests/test_identity_bootstrap_email.py` | CREATE | Hermetic email-validation tests — §11 tests 8–11. | §11, §5 | No | No — test code only |
| `backend/tests/test_identity_bootstrap_cli.py` | CREATE | Hermetic CLI argument/stdin tests — §11 tests 7, 12, 41, 42 (hermetic half). | §11, §4 | No | No — test code only |
| `backend/tests/test_identity_bootstrap_runtime_wiring.py` | CREATE | Hermetic composition-root wiring tests — §11 tests 44, 47, 49, 50, 51, 52. | §11, §6 | No | No — test code only |
| `backend/tests/live/test_identity_bootstrap_live.py` | CREATE | Real-PostgreSQL tests — §11 tests 1, 21, 23, 29, 30 (live half), 31, 32, 39, 40, 42 (live half). | §11 | No | No — test code only |
| `backend/tests/live/test_identity_bootstrap_concurrency_live.py` | CREATE | Real-PostgreSQL concurrency tests — §11 tests 35–38, 45. | §11 | No | No — test code only |

**No production file or test file outside these exact eleven enumerated paths (four production files, seven test files) may be created or modified by GD-016 implementation.** The mandatory rerun of existing suites (test 46) does not authorize modification of any existing test file — only execution of the existing suite as it stands. If implementation discovery shows any file outside these eleven exact paths must be touched to realize this package, implementation must STOP and return to Governance rather than expand the allowlist unilaterally.

## 4. CLI input contract

The command (`backend/app/contexts/identity/cli/bootstrap_first_tenant.py`) accepts exactly these inputs and no others:

| Input | Source | Validation | Governing requirement |
|---|---|---|---|
| Supabase access token | stdin only, or an equivalent protected file descriptor, closed immediately after read | Verified via the composition root's own `JwtVerifier` (§6) | Never a command-line argument; never logged; never placed in any audit payload or error text |
| Tenant name | operator CLI argument | Non-empty after `.strip()` | Matches `Tenant.new(name=...)`'s own normalization |
| Requested role | operator CLI argument | Must be exactly `compliance_officer` or `surveyor_general` | Enforced by the CLI's own parsing (fast operator feedback) **and**, authoritatively, by both PDP policies regardless of what the CLI accepted |
| Full name | operator CLI argument | Non-empty after `.strip()` | Plain check, no `AuthService` dependency |
| **Country** | **operator CLI argument — mandatory, no default** | `CountryCode(country.upper()).value` | This privileged bootstrap command does **not** fall back to the ordinary `AuthService.DEFAULT_COUNTRY` ("NG") default. The operator must supply an explicit ISO 3166-1 alpha-2 value every time; omission is a CLI usage error, not a silently-defaulted value. |
| **Email** | **not an operator argument at all — never accepted, never present in the CLI's argument parser** | Sourced exclusively from the verified JWT's own `email` claim, per §5 | An operator-supplied `--email` (or any similarly named) flag must not exist in this command's argument parser under any circumstance |

Fail-closed rule: if tenant name, role, full name, or country fails validation, the command exits with a clear operator-facing error and performs no PDP call, no session, and no audit write.

## 5. Verified email contract

The existing `JwtVerifier` (`backend/app/kernel/security/jwt.py`) validates `exp`, `iat`, `iss`, `aud`, `sub` — it does not require or validate an `email` claim. This Decision therefore binds the bootstrap command to the following exact sequence, performed immediately after successful cryptographic verification and before any PDP call:

1. Read `claims.get("email")` from the verified claims dict.
2. Require it to be present and a non-empty string after `.strip()` — a missing or blank claim is a fail-closed rejection, not a fallback to any other value.
3. Validate and normalize it using the existing public value object: `Email.parse(raw_email)` (`backend/app/contexts/identity/domain/value_objects.py`) — a malformed value (failing `Email`'s own regex) raises `ValueError`, which the command treats as a fail-closed rejection.
4. Use the resulting normalized `Email.parse(...).value` as: (a) the `email` field the command passes into its own hand-built `ExecutionContext` (§6 step 10), and (b) the email LandVault's `User.new(email=...)` receives for the new user row.
5. If any of steps 2–3 fails, the command fails closed **before** the first PDP call (`enforce("identity.bootstrap_preflight", ...)` is never invoked) and performs no audit write of its own (there is no verified-enough subject context to attribute one to at this point, consistent with `ADR-031` §"Token handling"/"Failure... semantics" on unattributable pre-verification failures). Critically, this also means **`set_context()` is never called** for any of these pre-binding failures (§6 step 11 is never reached) — see §6 step 15 and test 50 below.

An operator-supplied email of any kind is not part of the CLI contract (§4) and may never override, supplement, or be consulted alongside the verified claim.

## 6. Standalone CLI composition root (binding, exact)

Because the bootstrap command is a standalone process, not a FastAPI request, it must construct its own copies of exactly the following runtime pieces — the same pieces `app/main.py`'s `create_app()` already constructs, composed identically, with no new authorization engine and no FastAPI `Request` object anywhere in this path:

1. Obtain governed settings: `settings = get_settings()` (`app.kernel.config`).
2. Create the async engine: `engine = create_async_engine(str(settings.database_url))`.
3. Build the session factory: `session_factory = build_session_factory(engine)` (`app.kernel.db`).
4. **Before any call to `enforce()`**, configure the independent eager audit fallback: `configure_eager_fallback(EagerPostgresAuditStore(session_factory))` (`app.kernel.audit`, `app.kernel.audit_postgres`). `enforce()` always audits its decision through `audit()` (`app.kernel.authorization.pep`); `audit()` resolves its store via `get_audit_store()`, which raises `RuntimeError("audit store not configured")` if neither a context-bound store nor this eager fallback has been configured. This ordering — `configure_eager_fallback()` strictly before the first `enforce()` call — is a deterministic, mandatory wiring requirement of the CLI composition root itself, not an optional fallback behavior; it is covered by a deterministic positive ordering test and a negative probe proving an unconfigured store cannot silently permit an audited authorization to proceed (§11, tests 44 and 52).
5. Construct the JWKS provider: `jwks = SupabaseJWKSProvider(project_url=settings.supabase_project_url)` (`app.contexts.identity.adapters.supabase`).
6. Construct the verifier with exactly the same parameters `app/main.py` uses: `verifier = JwtVerifier(jwks=jwks, issuer=supabase_issuer(settings.supabase_project_url), audience=settings.supabase_jwt_audience, algorithms=[settings.supabase_jwt_algorithm])`.
7. Read the token from stdin (§4) and verify it directly: `claims = await verifier.verify(token)`. An `InvalidTokenError` here is a fail-closed rejection with no audit write and no `ExecutionContext` ever constructed or bound (no verified subject yet to attribute one to, and nothing yet to bind).
8. Validate and normalize the verified email exactly as §5 specifies. A failure here is likewise pre-binding: no `ExecutionContext` is constructed or bound.
9. Call the existing production hydrator for the verified subject: `hydrator = build_production_context_hydrator(session_factory)` (`app.contexts.identity.context_hydration`); `attrs = await hydrator(subject) or {}`.
10. Construct the bootstrap `ExecutionContext` by hand (no FastAPI dependency): `ExecutionContext(principal_id=subject, email=<normalized email from §5>, country=attrs.get("country"), tenant_id=attrs.get("tenant_id"), organization_id=attrs.get("organization_id"), roles=tuple(attrs.get("roles") or ()), attributes=attrs.get("attributes") or {})`. **`principal_id` is bound to `subject` — the cryptographically verified Supabase JWT `sub` — directly and unconditionally, never to `attrs.get("principal_id", subject)`.** This deliberately departs from `_build_context_from_token`'s own field-by-field construction on this one field: that private, `Request`-coupled function's `attrs.get("principal_id", subject)` fallback is correct for ordinary HTTP runtime behavior, where an already-provisioned active user's internal LandVault user id is the right authorization-attribute `principal_id` to carry forward. It is **not** the bootstrap actor-attribution rule `ADR-031` establishes (§9 below), under which every bootstrap audit event must record the verified Supabase subject itself, regardless of whether the hydrator also resolved an internal LandVault id for that subject. Hydrated `attrs` are used **only** for `country`, `tenant_id`, `organization_id`, `roles`, and `attributes`/delegated roles — never for `principal_id`. **This is the exact point at which the verified Supabase subject becomes the authoritative `principal_id` for every audit event this command will ever emit** — see §9's attribution rule.
11. Bind it: `token_ref = set_context(ctx)` (`app.kernel.context`). **This is the first point in the command's execution at which any bootstrap `ExecutionContext` exists in the ambient `ContextVar` at all.** Nothing before this step binds, manufactures, or installs a context merely so it can later be reset — a pre-binding failure (steps 7–8) leaves the ambient `ContextVar` state exactly as it was found.
12. Retain `token_ref` for cleanup.
13. Call `register_bootstrap_policies()` (from `bootstrap_policies.py`) — **only in this CLI process**. `app/main.py` is never modified to call this function; the FastAPI application process never registers either bootstrap action.
14. Proceed to Stage 1 via the existing, unmodified `enforce()` (`app.kernel.authorization.pep`).
15. In a `finally` block covering every exit path from step 11 onward — successful bootstrap, Stage-1 DENY, Stage-1 audit failure, override audit failure, Stage-2 DENY, Stage-2 audit failure, mutation/staged-audit failure, commit failure, or any other post-binding exception — call `reset_context(token_ref)` (`app.kernel.context`) exactly once (mandatory tests 49 and 51). This `finally` block's scope begins only after step 11 succeeds: for any failure in steps 7–8 (before `set_context()` is ever called), `reset_context()` must **not** be called, no bootstrap context was ever installed, and any previously existing ambient `ContextVar` state is left completely unchanged (mandatory test 50). The lifecycle rule is precise and binary: no binding, no reset, no ambient-state change, for every pre-binding failure; exactly one bind and exactly one reset, for every post-binding path.

No private function (`_build_context_from_token`, `_extract_bearer`, etc.) is imported or called. No parallel token-verification or context-hydration implementation is authorized — only this exact composition of already-existing public pieces.

## 7. Eager-audit / bootstrap-transaction ordering (binding, exact)

The bootstrap transaction and the eager audit path are **two separate sessions**, never one:

- **Bootstrap transaction** (its own `AsyncSession`, opened directly by `bootstrap_service.py`, never via `get_db_session()`):
  1. Begin transaction.
  2. Execute `SELECT set_config('app.is_super_admin', 'true', true)`.
  3. The **next SQL statement executed by this same bootstrap-transaction session** must be `LOCK TABLE tenants IN EXCLUSIVE MODE` — no other statement on this session may intervene between override activation and the lock.
  4. Then the `platform_empty` read (`SELECT count(*) FROM tenants`) under that same lock and override.

- **Eager audit session** (via the `EagerPostgresAuditStore` configured in §6 step 4 — its own, separate session/transaction, opened and committed independently by `audit()`): immediately after the bootstrap transaction's step 2 (override activation) and before its step 3 (the lock), the command emits `identity.bootstrap.rls_override_used` through `audit()`. Because this audit write happens on a **different session**, it is not a statement "executed by the bootstrap transaction" and therefore does not violate the "lock is the first statement after override activation" invariant — that invariant governs the bootstrap transaction's own statement sequence, not wall-clock ordering of unrelated sessions.

If this eager override-use audit write fails to become durable: fail closed, roll back the bootstrap transaction, and do not proceed to the privileged tenant-count read (step 3/4 above are never reached). This preserves `ADR-031`'s "narrow, gated, independently and durably audited" override requirement and `ADR-029`'s audit-durability invariants exactly, without requiring the override-use audit to share the bootstrap transaction's own session.

## 8. `audit_staged()` documentation synchronization

**Repository-conflict check performed**: `backend/app/kernel/audit_postgres.py` is inside `ADR-009`'s B1 freeze (`backend/app/kernel/`). This Decision's proposed change is a docstring-text edit only — zero executable statements, no function signature, no audit semantics change. This is the same category of later-decision-authorized, frozen-scope-file change `GD-010` already made to `backend/app/kernel/audit.py` (the DAG-aware `verify_chain()` rewrite), under the same precedent `ADR-031`'s own "Frozen-scope clarification" describes: a later, explicit governance instrument may narrowly extend frozen-scope documentation/behavior without amending `ADR-009` itself. **No conflict with any operative freeze requirement was found.** This documentation-only change does not amend `ADR-009`.

Upon merge of this Decision's implementation, the `audit_staged()` docstring's authorized-call-site sentence shall be updated from:

> "Must be called explicitly, by name, at an authorized call site only (GD-009 Batch 1: app.contexts.evidence.application.attribution_service. EvidenceActorAttributionService.record_attribution/correct_attribution)."

to exactly:

> "Must be called explicitly, by name, at an authorized call site only — currently: (GD-009 Batch 1) `app.contexts.evidence.application.attribution_service.EvidenceActorAttributionService.record_attribution`/`correct_attribution`; and (GD-016) `app.contexts.identity.application.bootstrap_service`'s two bootstrap successful-mutation call sites, staging `identity.tenant.bootstrapped` and `identity.user.registered`."

and the sentence "only by importing and calling this function directly, at the sites GD-009 authorizes" shall become "only by importing and calling this function directly, at the sites GD-009 and GD-016 authorize." No other line of that docstring, and no line of code anywhere in the file, changes.

## 9. Complete ten-step bootstrap flow (binding, exact — not abbreviated)

1. Verify the operator-supplied Supabase access token through the composition root's `JwtVerifier` (§6 steps 5–7), yielding verified `(identity_subject, claims)`.
2. Validate the verified email per §5; hydrate and bind the `ExecutionContext` per §6 steps 8–12.
3. Run `enforce("identity.bootstrap_preflight", resource={"requested_role": role}, env={"invocation_channel": "bootstrap_cli"})` (§6 step 14) — audited independently via the eager store configured in §6 step 4.
4. **Only on PERMIT**, begin the bootstrap transaction on its own session (never `get_db_session()`), connected as the ordinary `landvault_app` role.
5. Execute `SELECT set_config('app.is_super_admin', 'true', true)` on that bootstrap-transaction session.
6. Immediately after step 5 and before step 7, emit `identity.bootstrap.rls_override_used` through the eager audit path (§7) — on its own, separate session. On failure to persist, fail closed and roll back; do not proceed to step 7.
7. On the bootstrap-transaction session, as its next statement, `LOCK TABLE tenants IN EXCLUSIVE MODE`, then `SELECT count(*) FROM tenants` to determine `platform_empty`, under that lock and override.
8. Run `enforce("identity.bootstrap_first_tenant", resource={"requested_role": role}, env={"preflight_permitted": True, "platform_empty": platform_empty})` — audited independently via the same eager store.
9. **Only on PERMIT**, on the bootstrap-transaction session, in exactly this order — preserving the same mutual-FK-avoidance sequence `ADR-010`/`register_local` already establish, never a deferred-constraint trick:
   a. `tenant = Tenant.new(name=tenant_name)`;
   b. persist/add the `Tenant` row while `tenant.owner_user_id` is still `None` — no owner reference may be persisted before the row it would reference exists;
   c. construct `user = User.new(identity_subject=<verified Supabase subject>, email=<normalized verified email>, full_name=<full name>, country=<explicit operator-supplied country>, tenant_id=tenant.tenant_id)`;
   d. immediately set `user.roles = [requested_role]` — never `user.assign_role(...)`, which would append to `User.new()`'s default `[general_user]` rather than replace it;
   e. persist/add the `User` row;
   f. only now that the referenced `User` row exists, set `tenant.owner_user_id = user.user_id` and persist/update the `Tenant` row;
   g. stage exactly `identity.tenant.bootstrapped` and `identity.user.registered` via `audit_staged(session, ...)` into this same transaction.
10. Commit on PERMIT (Tenant, User, owner-FK, and both staged audit events together) or roll back on any failure before commit. The `EXCLUSIVE` lock and the `app.is_super_admin` GUC are both released automatically at transaction end, regardless of outcome. In every case, the `finally` block from §6 step 15 resets the `ExecutionContext` if and only if it was ever bound.

The requested role is constrained to exactly `compliance_officer` or `surveyor_general` by both PDP policies independent of what the CLI itself validated (§4). The final persisted `User.roles` equals exactly `[requested_role]` — never `[general_user, requested_role]`, and never containing `super_admin` under any path.

**Actor-attribution rule (binding):** every audit event this command produces — both independent/eager (`authz.permit`/`authz.deny` for each PDP stage, `identity.bootstrap.rls_override_used`) and transaction-coupled (`identity.tenant.bootstrapped`, `identity.user.registered`) — carries, as its `principal_id`, the verified Supabase subject whose credential authorized the operation, sourced exclusively from `ExecutionContext.principal_id = subject` as bound in §6 step 10. **This holds even when the production hydrator resolves a different, already-provisioned internal LandVault user id for the same subject** — that hydrated id is used for `tenant_id`/`roles`/`country`/`organization_id`/`attributes` only (§6 step 10), and must never leak into `principal_id` for any event this command emits, including a Stage-1 DENY issued precisely because that hydrated identity already has an effective tenant/roles. No other source of identity (an operator argument, an environment variable, a CLI flag, or a hydrated internal id) may ever populate `principal_id` for any event this command emits (mandatory test 43, strengthened to include this adversarial hydrator case and its Stage-1 DENY sub-case — see §11).

## 10. Complete STOP conditions

Implementation must STOP and return to Governance, without improvising a workaround, if any of the following holds:

1. **(A) Pre-ratification drift**: `origin/main` differs from the GD-016 architecture-review/ratification baseline (§1) at the time Governance Authority ratification is sought, and this Decision has not been revalidated against the new repository state. **(B) Post-publication drift**: the exact `main` SHA pinned by the separate implementation branch/worktree authorization (§13), taken immediately after this Decision's own ratified text is merged, has moved before implementation actually begins.
2. Any file in the §3 allowlist already exists with conflicting semantics.
3. Implementation requires modifying any file outside the exact §3 allowlist.
4. Implementation requires changing PDP or PEP behavior (`pdp.py`, `pep.py`).
5. Implementation requires changing any existing default policy's code or priority (10, 11, 20, 30, 40).
6. Implementation requires changing `get_db_session()` (`uow.py`).
7. Implementation requires modifying existing registration/invitation behavior (`register_local`, `accept_invitation_supabase`, `_provision_user_from_invitation`, `_validate_profile`).
8. Implementation requires a database migration of any kind.
9. Implementation requires a new table, column, index, foreign key, RLS policy, grant, or persistent bootstrap flag/sentinel.
10. Implementation requires an HTTP route.
11. Implementation requires the Supabase Admin API.
12. Implementation requires a new third-party dependency.
13. Implementation requires an operator-supplied email argument.
14. Implementation requires a role outside `{compliance_officer, surveyor_general}`.
15. Implementation requires any `audit_staged()` call site beyond the two named in §8.
16. Implementation cannot preserve eager-audit durability as specified in §6 step 4 and §7.
17. Implementation cannot preserve Stage-1-PERMIT-before-override ordering (§9 steps 3–5).
18. Implementation cannot preserve the lock-is-next-bootstrap-transaction-statement requirement (§7, §9 step 7).
19. Implementation cannot satisfy the mandatory real-PostgreSQL concurrency tests (§11, tests 35–38, 39–40, 45).
20. Repository reality at implementation time conflicts with `ADR-031` or `ADR-032` in any way not already reconciled by this Decision.
21. Any mandatory test cannot be made to pass without broadening this Decision's authority beyond §3's allowlist.

No improvisation is authorized after any STOP condition is reached.

## 11. Complete mandatory test matrix

| # | Purpose | Expected outcome | Classification | Exact file |
|---|---|---|---|---|
| 1 | Empty-platform bootstrap, `compliance_officer` or `surveyor_general`, full flow | Succeeds end-to-end; Tenant+User+owner-FK+both staged audits committed, with the exact §9 step 9 persistence order observed directly against real PostgreSQL: `Tenant` row exists (with `owner_user_id IS NULL`) before the `User` row is inserted, and `tenant.owner_user_id` is updated to the committed `User`'s id only after that `User` row exists | REAL POSTGRESQL | `backend/tests/live/test_identity_bootstrap_live.py` |
| 2 | Requested role `compliance_officer` | Stage 1 & 2 PERMIT; final `user.roles == ["compliance_officer"]` | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_policies.py` |
| 3 | Requested role `surveyor_general` | Stage 1 & 2 PERMIT; final `user.roles == ["surveyor_general"]` | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_policies.py` |
| 4 | Requested role `general_user` | Explicit DENY at Stage 1 | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_policies.py` |
| 5 | Requested role `super_admin` | Explicit DENY at Stage 1, before `platform.super_admin` (priority 20) is reached | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_policies.py` |
| 6 | Every other/unknown role string | Explicit DENY | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_policies.py` |
| 7 | Malformed/expired JWT | Verification fails before step 2; no PDP call, no audit write, no `ExecutionContext` bound | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_cli.py` |
| 8 | Verified claims missing `email` entirely | Fails closed before first `enforce()` call; no `ExecutionContext` bound | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_email.py` |
| 9 | Blank/whitespace-only `email` claim | Fails closed before first `enforce()` call; no `ExecutionContext` bound | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_email.py` |
| 10 | Malformed `email` claim (fails `Email.parse`'s regex) | Fails closed before first `enforce()` call; no `ExecutionContext` bound | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_email.py` |
| 11 | Valid `email` claim with mixed case/whitespace | Normalized via `Email.parse(...).value`; used for both `ExecutionContext.email` and `User.new(email=...)` | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_email.py` |
| 12 | CLI argument parser inspected for an email-accepting flag | No such flag exists under any name | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_cli.py` |
| 13 | Authenticated subject with existing effective tenant/roles | Explicit DENY at Stage 1 (`ctx.tenant_id`/`ctx.roles` not empty) | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_policies.py` |
| 14 | Suspended/inactive local identity shape | Not mistaken for platform-emptiness proof; `platform_empty` remains the sole authoritative fact | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_policies.py` |
| 15 | Stage-1 matching-action condition failure | Explicit DENY (never `None`) | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_policies.py` |
| 16 | `super_admin` + `identity.bootstrap_preflight` | Explicit DENY before priority-20 `platform.super_admin` is reached | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_policies.py` |
| 17 | Unrelated action (e.g. `registry.parcel.read`) + `super_admin` | `platform.super_admin` still PERMITs, unchanged | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_policies.py` |
| 18 | Wrong/missing `invocation_channel` | Explicit DENY | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_policies.py` |
| 19 | Stage-1 DENY | Override never activated (step 5 never reached) | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_service.py` |
| 20 | Stage-1 audit-write failure (mocked eager store) | Override never activated; fails closed | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_service.py` |
| 21 | Override-use audit durable | `identity.bootstrap.rls_override_used` persists, on its own session | REAL POSTGRESQL | `backend/tests/live/test_identity_bootstrap_live.py` |
| 22 | Override-use audit-write failure (mocked eager store) | Fails closed before the `tenants` probe; bootstrap transaction rolled back | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_service.py` |
| 23 | `platform_empty` evaluated under active override and lock | Correct authoritative value observed | REAL POSTGRESQL | `backend/tests/live/test_identity_bootstrap_live.py` |
| 24 | Final PDP, `platform_empty=False` | Explicit DENY | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_policies.py` |
| 25 | Final-PDP audit-write failure (mocked) | Fails closed; rollback; no mutation | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_service.py` |
| 26 | Final user's `roles` | Equals exactly `[requested_role]` | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_service.py` |
| 27 | Final user does not retain `general_user` | Confirmed absent from final `roles` | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_service.py` |
| 28 | Final user never receives `super_admin` | Confirmed absent under every tested path | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_service.py` |
| 29 | Tenant + User + owner-FK + both staged audits | Commit atomically, together; final committed state explicitly verified to show the §9 step 9 persistence order (Tenant inserted before User, `owner_user_id` set only after the User row exists), with no owner reference ever pointing at a non-existent User row at any intermediate point within the transaction | REAL POSTGRESQL | `backend/tests/live/test_identity_bootstrap_live.py` |
| 30 | Staged-audit failure (forced) | Rolls back Tenant, User, owner-FK, and both staged events together | UNIT/HERMETIC (mocked) + REAL POSTGRESQL | `backend/tests/test_identity_bootstrap_service.py`, `backend/tests/live/test_identity_bootstrap_live.py` |
| 31 | Forced commit failure | No successful-mutation domain or audit state survives | REAL POSTGRESQL | `backend/tests/live/test_identity_bootstrap_live.py` |
| 32 | Independent (eager) audit evidence vs. later mutation rollback | Independent evidence survives; staged evidence does not | REAL POSTGRESQL | `backend/tests/live/test_identity_bootstrap_live.py` |
| 33 | Second bootstrap after a prior success | Fails closed (Stage 1 and/or Stage 2) | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_service.py` |
| 34 | Failed first attempt, platform still empty | Safely retryable; succeeds on retry | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_service.py` |
| 35 | Bootstrap vs. bootstrap concurrency | Exactly one successful bootstrap | REAL POSTGRESQL | `backend/tests/live/test_identity_bootstrap_concurrency_live.py` |
| 36 | Bootstrap vs. ordinary tenant-creator `INSERT` | Serialized correctly by the `EXCLUSIVE` lock | REAL POSTGRESQL | `backend/tests/live/test_identity_bootstrap_concurrency_live.py` |
| 37 | ADR-031 Race A | Demonstrated against real PostgreSQL | REAL POSTGRESQL | `backend/tests/live/test_identity_bootstrap_concurrency_live.py` |
| 38 | ADR-031 Race B | Demonstrated against real PostgreSQL | REAL POSTGRESQL | `backend/tests/live/test_identity_bootstrap_concurrency_live.py` |
| 39 | Transaction-local GUC after commit | Clears | REAL POSTGRESQL | `backend/tests/live/test_identity_bootstrap_live.py` |
| 40 | Transaction-local GUC after rollback | Clears | REAL POSTGRESQL | `backend/tests/live/test_identity_bootstrap_live.py` |
| 41 | Router/mount inspection | No HTTP route exposes either bootstrap action | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_cli.py` |
| 42 | Token presence check across argv, logs, audit payloads, error text | Absent in every case | UNIT/HERMETIC + REAL POSTGRESQL (log capture) | `backend/tests/test_identity_bootstrap_cli.py`, `backend/tests/live/test_identity_bootstrap_live.py` |
| 43 | Audit `principal_id` on every emitted event, **including the adversarial case where the hydrator deliberately returns a different internal LandVault `principal_id` for the verified subject** (a fake hydrator returning `attrs["principal_id"] = "<some other internal user id>"`), and **including a Stage-1 DENY case for an already-provisioned active identity** (hydrator additionally returns a non-empty `tenant_id`/`roles` for that same subject, so Stage 1 explicitly DENYs per §9 step 3) | In every case — PERMIT, DENY, override-use, and both staged successful-mutation events — `principal_id` equals the verified Supabase `sub`, never the hydrated internal LandVault id, per the actor-attribution rule in §9 | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_service.py` |
| 44 | Deterministic wiring: CLI composition root calls `configure_eager_fallback(EagerPostgresAuditStore(session_factory))` strictly before its first call to `enforce(...)` | Ordering assertion passes on every run — `configure_eager_fallback` is observed (e.g. via spy/mock call-order capture) to execute before the first `enforce()` invocation; this is not an alternative among acceptable outcomes, it is the sole required outcome | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_runtime_wiring.py` |
| 45 | `verify_chain()` after bootstrap audit entries added | Remains valid | REAL POSTGRESQL | `backend/tests/live/test_identity_bootstrap_concurrency_live.py` |
| 46 | Existing Identity/authorization/audit/invitation suites | Remain green, unmodified | full existing suite rerun | (no new file — existing `backend/tests/` suite) |
| 47 | Bootstrap policies registered check against the normal FastAPI app-factory path | Confirmed **not** registered; `app/main.py` import/startup inspected | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_runtime_wiring.py` |
| 48 | Unrelated action, ordinary authenticated user | PDP behavior byte-for-byte unchanged from pre-GD-016 behavior | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_policies.py` |
| 49 | `ExecutionContext` reset on successful bootstrap (post-binding path) | `reset_context()` called exactly once via `finally` | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_runtime_wiring.py` |
| 50 | **Pre-binding failures never bind or reset a context** — malformed/expired JWT, missing email claim, blank email claim, malformed email claim, and any other pre-binding validation failure | `set_context()` is never called; `reset_context()` is correspondingly never called; no bootstrap `ExecutionContext` is installed at any point; any previously existing ambient `ContextVar` state is observed unchanged after the failure | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_runtime_wiring.py` |
| 51 | **Post-binding failures always reset exactly once** — Stage-1 DENY, Stage-1 audit-write failure, override-use audit-write failure, Stage-2 DENY, Stage-2 audit-write failure, mutation/staged-audit failure, commit failure, and any other post-binding exception | `reset_context(token_ref)` is called exactly once via `finally` on each of these paths, with no double-reset and no skipped reset | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_runtime_wiring.py` |
| 52 | **Negative probe: eager audit store left unconfigured** | With `configure_eager_fallback(...)` never called, an attempted audited authorization (`enforce()`/`audit()`) cannot silently proceed as if audited — it surfaces a hard failure (`get_audit_store()`'s `RuntimeError("audit store not configured")` propagating out of `enforce()`) rather than permitting the PDP decision to take effect unaudited | UNIT/HERMETIC | `backend/tests/test_identity_bootstrap_runtime_wiring.py` |

## 12. Explicit non-authorizations

This Decision does not authorize: any modification to `backend/app/kernel/authorization/{pdp,pep,policies}.py` or `backend/app/kernel/uow.py`; any modification to `register_local`, `accept_invitation_supabase`, `_provision_user_from_invitation`, `_validate_profile`, `User.new()`, or `User.assign_role()`; any modification to `backend/app/kernel/audit_postgres.py` beyond the exact docstring text in §8; any new HTTP route; any Supabase Admin API integration; any database migration; any role outside `{compliance_officer, surveyor_general}`; any `audit_staged()` call site beyond the two named in §8/§9; registering the bootstrap policies in the FastAPI application process (`app/main.py`); an operator-supplied email argument of any kind; a default country value for this command; production bootstrap execution; or closure of MVP-DEMO-002 (§14).

## 13. Phase gates (unshortened)

This Decision's own governance-publication sequence, and the subsequent implementation sequence it gates, are two distinct chains, run end to end, in this exact order:

**Governance-publication sequence (publishes GD-016 itself as a repository record):** GD-016 remediated proposal → independent governance review → Governance Authority ratification → GD-016 ratification-recording authorization → record GD-016 in repository → commit authorization → commit → push authorization → push → PR authorization → human approval/CI → merge authorization → merge → post-merge verification.

**Implementation sequence (gated on the governance-publication sequence having completed):** implementation branch/worktree authorization (pinning the exact post-GD-016-publication `main` SHA per §1(B)) → implementation → tests → independent implementation review → implementation acceptance → commit authorization → commit → push authorization → push → PR authorization → human review/CI → merge authorization → merge → post-merge verification → MVP-DEMO-002 rerun.

No gate in either sequence may be collapsed or skipped, and the implementation sequence may not begin before the governance-publication sequence has completed.

## 14. MVP-DEMO-002 closure

Implementation success does not close MVP-DEMO-002. Merge does not close MVP-DEMO-002. Only a later, separately recorded successful end-to-end rerun using the legitimate bootstrap mechanism, after independent post-merge verification, may close it.

## 15. Traceability matrix

| `ADR-031`/`ADR-032` requirement | Exact production file | Exact test(s) | GD-016 authority clause |
|---|---|---|---|
| Ten-step bootstrap sequence | `bootstrap_service.py` | 1, 29, 35–38 | §9 |
| Action-owning, explicit-DENY bootstrap policies (`ADR-032`) | `bootstrap_policies.py` | 4–6, 13–18, 24, 48 | §3, §9 |
| Priorities 15/16 before `platform.super_admin` (20) | `bootstrap_policies.py` registration | 16, 17 | §3 |
| PERMIT-before-override ordering, not `get_db_session()` | `bootstrap_service.py` | 19, 20, 39, 40 | §7, §9 steps 3–5 |
| Lock-is-next-bootstrap-statement / eager-audit-session separation | `bootstrap_service.py` | 21, 22, 23 | §7 |
| `EXCLUSIVE` lock / Race A / Race B | `bootstrap_service.py` | 35–38 | §9 step 7 |
| `identity.bootstrap.rls_override_used` audit | `bootstrap_service.py` | 21, 22 | §7, §9 step 6 |
| Two category-B staged audit events | `bootstrap_service.py` | 29, 30 | §9 step 9 |
| `audit_staged()` call-site documentation | `audit_postgres.py` (docstring only) | — (code review check, no runtime test) | §8 |
| No HTTP route | `cli/bootstrap_first_tenant.py`; `app/main.py` unchanged | 41 | §4, §12 |
| Token via stdin only, never logged | `cli/bootstrap_first_tenant.py` | 7, 42 | §4 |
| Verified email, `Email.parse`, no CLI override | `cli/bootstrap_first_tenant.py`, `bootstrap_service.py` | 8–12 | §5 |
| Explicit country, no default | `cli/bootstrap_first_tenant.py` | (covered by CLI argument-parsing tests in `test_identity_bootstrap_cli.py`) | §4 |
| Role allowlist, exact final role set | both PDP policies + `bootstrap_service.py` | 2, 3, 26–28 | §3, §9 step 9 |
| CLI composition root (engine/session factory/verifier/hydrator) | `cli/bootstrap_first_tenant.py` | 44, 47, 52 | §6 |
| Eager audit fallback configured before first `enforce()` | `cli/bootstrap_first_tenant.py` | 44, 52 | §6 step 4, §7 |
| `ExecutionContext` bind/reset lifecycle (pre-binding vs. post-binding) | `cli/bootstrap_first_tenant.py` | 49, 50, 51 | §6 steps 10–15 |
| Bootstrap policies never registered in FastAPI process | `app/main.py` unchanged; CLI self-registers | 47 | §6 step 13, §12 |
| `principal_id` attribution | `bootstrap_service.py` | 43 | §9 (actor-attribution rule) |
| `verify_chain()` compatibility | no change to `audit.py` | 45 | §12 (denylist) |
| No migration | no migration file created | — | §3, §10 |
| Existing suites remain green | no change to existing Identity/kernel files beyond §8 | 46 | §12 |

GD-016 — RATIFIED / ACCEPTED — 28 OCTOBER 2026 — IN FORCE
