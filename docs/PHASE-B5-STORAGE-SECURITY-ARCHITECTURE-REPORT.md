# SUPABASE STORAGE SECURITY ARCHITECTURE REPORT

**Mode:** Architecture analysis / ADR draft only. No code, SQL, environment, dependency, or
RLS change was made. PR #22 was not modified. Nothing was merged.

## Document status and history

This report captures the analysis performed when ADR-027 was first drafted as **PROPOSED**. It is
retained here as the **evidence/history record of how the decision was reached**, not edited
retroactively to make the eventual answer look obvious from the outset — the investigation
genuinely had to establish, rather than assume, that PR #22's original claim was wrong (§2) and
that a database-backed second layer was feasible in principle but blocked by an unverified
precondition (§4) before a staged recommendation could be responsibly made (§10).

Two things happened after this report was written, and this document is **not** updated to
pretend they happened simultaneously with the original analysis:

1. **Governance ran a ratification-readiness review** that found the original draft's pilot
   boundary was not stated as a self-expiring exception, its test-requirement language ("a
   Storage-layer cross-tenant test") could be misread as implying Storage-level tenant protection
   that does not exist under the pilot model, and it lacked an incident-response procedure and a
   periodic re-attestation requirement. The ADR was revised to close each of these gaps — see
   `docs/adr/ADR-027-supabase-storage-authorization-and-tenant-isolation.md` §10 and §11 for the
   corrected text.
2. **Governance Authority ratified the revised ADR-027 as Accepted, 2026-09-06.** The
   recommendation below (§10) and the underlying analysis (§§1–9) are unchanged in substance by
   ratification; the ADR file is the authoritative, current statement of the governing
   architecture, including its self-expiring pilot conditions and three named hard gates
   (§10.6.1–§10.6.3 there). Where this report's own wording is looser than the ratified ADR's
   (for example, its original single-sentence description of the production gate below, or its
   "storage-layer cross-tenant test" phrasing in §11), **the ADR governs.**

## 1. ADR inventory (verified against `docs/adr/`, current `main`)

ADR-001 through ADR-019 exist. **ADR-020 is deliberately, permanently vacant** — recorded in
`docs/EXECUTION_PLAN.md` §11.3 and `docs/GOVERNANCE_BASELINE.md` §B.5 as "the record that a
question is open... not to be filled by any automatic allocator." ADR-021 through ADR-026 exist.
**Next available number: ADR-027.** (This was verified, not assumed — ADR-020's vacancy is exactly
the kind of trap a naive "highest + 1" allocator would fall into by filling it.)

**Proposed ADR:** ADR-027 — *Supabase Storage Authorization and Tenant Isolation*. Full draft
below and at `docs/adr/ADR-027-supabase-storage-authorization-and-tenant-isolation.md`.

## 2. Factual correction to PR #22's original assumption

PR #22 states its Storage security model is "the identical... pattern ADR-025 E2 already
established for Postgres RLS, applied to a second resource" and treats this as "not a new
architecture decision." This is incorrect. Reading the actual mechanism:

- **Postgres RLS here** is a same-connection backstop: the backend's own trusted connection sets
  `current_setting('app.tenant_id')` via `SET LOCAL`/`set_config` (`backend/app/kernel/uow.py`)
  before every query; every RLS policy (migrations `0001`, `0005`, `0006`, `0012`) simply checks
  that value. It catches "the backend forgot to filter" bugs. It does not involve a second
  credential.
- **Supabase Storage's native RLS** is keyed on `auth.uid()`, populated only when a caller
  presents a Supabase-issued end-user JWT **directly to the Storage API**. `SupabaseStorageAdapter`
  never does this — it always authenticates with `SUPABASE_SERVICE_ROLE_KEY`, which is an
  unconditional RLS bypass by Supabase's own design.

These are two different mechanisms that happen to share the name "RLS." Postgres has two
enforcement layers (PDP/PEP, then the tenant-filter backstop). Storage today has **one**
(PDP/PEP only) — the analogy in PR #22 does not hold, and the corrected finding is: **the current
Storage layer supplies zero independent backstop**, not "the same backstop applied to a second
resource."

## 3. Actual current Storage trust model

FastAPI authorizes every Evidence operation (PDP/PEP + `EvidenceService`'s creator-or-governance/
tenant-scope check) before ever calling `StoragePort`. `SupabaseStorageAdapter` then authenticates
to a private bucket (`infra/supabase/evidence_bucket.sql`, `anon`/`authenticated` denied entirely)
using the service-role key. No browser code path reaches Storage directly. This is a coherent,
single-layer trusted-backend model — but it is one layer, not two, for a resource LV-000 Article
XI §1 treats as tenant-scoped and requiring two.

## 4. Database/policy feasibility findings (the core technical question)

Investigated rather than assumed, per the governing instruction:

- `identity_users.identity_subject` already stores the Supabase `sub` claim (renamed from
  `keycloak_subject` in migration `0013`) — this is exactly the value `auth.uid()` returns for a
  Supabase-authenticated caller. **The `auth.uid() → internal user → tenant` mapping already
  exists and needs no new column or mechanism.**
- A `SECURITY DEFINER` SQL function with a pinned `search_path`, reading `identity_users`/
  `tenants` directly, is a supported and documented way to let a `storage.objects` policy validate
  an object key's tenant segment against LandVault's own authoritative tables — **without** any
  JWT tenant claim. This is technically feasible in principle.
- **The blocking precondition:** this requires Storage's `storage.objects` and the application's
  `identity_users`/`tenants` tables to live in the **same database/project**. `Settings.
  database_url` and `Settings.supabase_project_url` are configured independently, and
  `evidence_bucket.sql` states plainly that no live Supabase project exists in this implementation
  environment. This cannot be confirmed by repository inspection — it is a fact about the pilot's
  actual Supabase provisioning, unresolved today.
- **Conclusion:** a database-lookup-based Storage RLS design (Option B) is a real, superior-in-
  principle alternative to custom JWT tenant claims and should be preferred **once buildable** —
  but it is not buildable or testable today given the unverified precondition above.

## 5. Service-role option (Option A) — evaluated

Simple, deployable now, keeps all authority in the existing PDP/PEP, no tenant data in any JWT,
fully server-controlled object keys. Its cost is real and should not be minimized: zero
independent backstop against a defect in this backend's own authorization or key-construction
logic — the exact class of bug Postgres's RLS backstop exists to catch, uncaught here. See the ADR
§3/§5 for the full risk list and required compensating controls.

## 6. User-JWT/Storage-RLS option (Option B) — evaluated

Forwards the caller's own verified Supabase token to Storage instead of the service-role key;
Storage RLS independently re-checks tenant match via the lookup function in §4. This is the only
option offering genuine independent failure containment (full threat matrix in the ADR, §5). Not
adopted for pilot only because of the unverified same-project precondition — pre-authorized as the
mandatory production gate.

## 7. Custom-claim option (Option 3) — evaluated separately, rejected

Embedding tenant/role in the Supabase JWT was evaluated on its own, not folded into Option B. It
conflicts with Article X's "re-resolved fresh on every request, never cached" discipline (a claim
is stale until token refresh) and with ADR-004's Postgres-sourced-attributes model, and closes no
feasibility gap that Option B's database-lookup approach doesn't already close without it.
Rejected; would require a new ADR with a materially different justification to reconsider.

## 8. Privileged-access analysis

Under Option A, privileged/governance cross-tenant workflows already work unchanged — the
service-role key has full reach and PDP/PEP already permits the relevant roles per ADR-011/
ADR-015. Under Option B, the same `SECURITY DEFINER` function that performs the ordinary
tenant-match check gets one additional branch recognizing governance/`super_admin` roles —
mirroring exactly how `app.is_super_admin` is a second disjunct in every existing Postgres RLS
policy, kept to one narrow, named, auditable exception (LV-000 Article IX §3) rather than
duplicating ADR-011's full delegation logic into SQL.

## 9. Threat matrix and scoring

See ADR §5 (threat/containment matrix) and §9 (0–10 scoring across 13 criteria). Summary: Option B
outscores Option A on every isolation-relevant criterion but scores near-zero on pilot feasibility
today because of the unverified same-project precondition; Option A scores strongly on
deployability but concedes defense-in-depth for Storage. The scores are not mechanically summed —
see the ADR's decision rationale.

## 10. Selected recommendation

**Staged model.** Pilot (Ehime Mbano) proceeds on Option A as an explicitly named, time-boxed
Controlled-Platform-Authority-style exception to Article XI §1 — not a claim that Option A already
satisfies it — gated on the compensating controls in ADR §10.1 (private bucket, no direct browser
path, server-generated keys, PDP/PEP-before-Storage, a new adapter-level test proving the adapter
performs no tenant validation of its own, and corrected documentation that stops claiming parity
with Postgres RLS). Option B is pre-authorized in shape as the mandatory production gate, forced
by the first of: onboarding a second tenant, any browser-direct-Storage code path, or confirmation
that a live Supabase project shares one database between Storage and the application tables.
Custom JWT tenant claims are rejected outright.

## 11. Exact PR #22 remediation

**No `StoragePort`/`SupabaseStorageAdapter` method signature change, and no SQL change to
`evidence_bucket.sql`.** Required before merge:

1. Correct `SupabaseStorageAdapter`'s module docstring and `evidence_bucket.sql`'s comment block —
   both currently claim parity with Postgres RLS that §2 above shows is false. Cite ADR-027
   instead and state plainly that Storage has one enforcement layer today, accepted as a named
   pilot exception.
2. Add a Storage-layer (not just HTTP-layer) cross-tenant test that documents, as an explicit
   invariant, that `SupabaseStorageAdapter` performs no tenant validation of its own — today's
   `test_cross_tenant_upload_denied`/`test_cross_tenant_list_denied` only prove the PDP/PEP layer
   denies.
3. Confirm (as a documented control, not just present behavior) that `SUPABASE_SERVICE_ROLE_KEY`
   is server-only, never logged, never sent to the frontend — already true in the adapter; make it
   a stated, tested invariant.
4. Add a credential-rotation runbook reference for the service-role key before pilot go-live
   (documentation, not code).
5. **Remove the unnecessary `SEALED` case in `artifacts/landvault-web/src/components/ui/
   status-badge.tsx`** — its own comment already states IMVP-5 "never reaches SEALED (no code path
   calls seal())"; it is dead code for this slice and should be removed, independent of the
   Storage decision.

None of the above was implemented in this task, per instruction.

---

## PROPOSED ADR (full text also at `docs/adr/ADR-027-supabase-storage-authorization-and-tenant-isolation.md`)

See that file for the complete draft: context, constitutional constraints, current architecture,
options considered, threat analysis, decision, rationale, credential model, tenant-enforcement
model, Storage policy model, privileged-access model, object-key rules, required controls, test
requirements, pilot limitations, production gate, consequences, rejected alternatives, and
relationship to ADR-004/ADR-025/ADR-026 and non-effect on B5.4+.

---

**STORAGE SECURITY ADR DRAFTED — READY FOR GOVERNANCE REVIEW**

*(Superseded by ratification: Governance Authority accepted the revised ADR-027 on 2026-09-06.
This original verdict line is left as written for the historical record — see "Document status
and history" above for what changed between this draft and the ratified text.)*
