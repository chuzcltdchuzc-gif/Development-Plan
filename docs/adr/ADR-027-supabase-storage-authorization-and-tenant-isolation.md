# ADR-027 — Supabase Storage Authorization and Tenant Isolation

**Status:** **ACCEPTED — 2026-09-06, on explicit Governance Authority ratification.** Adopted as
the governing architecture for ordinary Evidence Storage authorization and tenant isolation for
AquaSavannah LandVault, subject in full to the pilot limitations and hard gates in §10. Acceptance
of this ADR does not merge or approve PR #22 — see §13 and the Ratification Record below for
what remains outstanding.

**Date:** 2026-09-06 (drafted); revised same day against Governance's ratification-readiness
review (tighter framing of the pilot boundary, the hard gates, the compensating controls, and the
test requirements); ratified same day by Governance Authority without further substantive change.

## Ratification Record

Ratified by Governance Authority for AquaSavannah LandVault, 2026-09-06, as: "ADR-027 — Supabase
Storage Authorization and Tenant Isolation... adopted as the governing architecture for ordinary
Evidence Storage authorization and tenant isolation, subject to the explicit pilot limitations and
hard gates contained within the ADR." The ratifying decision restates, and does not alter, §§1–14
below; it additionally makes explicit that credentials must never enter Git (folded into §10.2),
and that ratification is a distinct governance act from merging PR #22 (§13 remains fully in
force — CI, live Supabase rehearsal, browser acceptance, human approval, and the final Governance
merge gate are unaffected by this ratification and are not satisfied by it).

**Extends:** `docs/adr/ADR-025-supabase-platform-baseline.md` E3. ADR-025 E3 selected Supabase
Storage as the primary `StoragePort` adapter for ordinary evidence but explicitly decided nothing
about its authorization/trust model. **This ADR fills that gap; it is not evidence that ADR-025
already made this decision, and must not be cited as such.**

**Does not decide:** WORM, sealing, Cloudflare R2, immutable archive, retention, legal hold,
break-glass cross-tenant evidence access, or any B5.4+ capability. Supabase Storage authorization
does not make storage WORM-grade, and this ADR makes no such claim. None of B5.4/WORM/R2 is
touched, implicated, or advanced by this ADR in any respect.

**Constitutional anchors:** LV-000 v1.0 Article VI §1 (Architecture Before Code); Article IX §2
(Security by Design), §3 (Controlled Platform Authority — every exception minimal, explicitly
documented, auditable, reviewable, expiring); Article X (exactly one authorization path — the
PDP/PEP/PIP engine; no parallel authorization system, ever, even temporarily); Article XI §1
(tenant isolation absolute by default, two independent layers for every tenant-scoped resource).

---

## 1. Context

IMVP-5 (PR #22, `feat/imvp-5-evidence-vertical-slice`) connects the already-accepted
`EvidenceRecord` domain model (ADR-026) to a real upload/list journey. PR #22's own description
frames its Storage adapter's security model as "the identical... pattern ADR-025 E2 already
established for Postgres RLS, applied to a second resource." That framing is incorrect, and this
ADR exists to correct it and supply the missing decision.

### 1.1 What ADR-025 E2 actually describes for Postgres

Postgres RLS in this codebase is a same-connection backstop: the backend's one privileged database
connection (`database_url`) itself executes `SELECT set_config('app.tenant_id', ...)` (and, on a
small number of named Controlled-Platform-Authority paths, `app.is_super_admin`) before every
query (`backend/app/kernel/uow.py`). Every RLS policy from migration `0001` onward is the single
predicate `tenant_id = current_setting('app.tenant_id', true) OR current_setting
('app.is_super_admin', true) = 'true'`. This catches "the backend forgot to filter" bugs. It is
not, and was never claimed by ADR-025 E2 to be, a second credential-based trust boundary.

### 1.2 What the current Storage adapter actually does

`SupabaseStorageAdapter` (`backend/app/contexts/evidence/adapters/supabase_storage.py`)
authenticates to Supabase Storage with `SUPABASE_SERVICE_ROLE_KEY` for every call — an
unconditional Storage-RLS bypass by Supabase's own design. `infra/supabase/evidence_bucket.sql`
grants no policy to `anon`/`authenticated` at all. **Postgres has two enforcement layers here
(PDP/PEP, then the tenant-filter backstop); Storage today has one (PDP/PEP only).** PR #22's
analogy does not hold, and must not be repeated as though it does.

### 1.3 Why Storage RLS cannot simply mirror Postgres RLS today

Postgres RLS here is keyed on `current_setting('app.tenant_id')`, a value only the backend's own
trusted connection sets. Supabase Storage's native RLS is keyed on `auth.uid()`, populated only
when a caller presents a Supabase-issued end-user JWT **directly to the Storage API**. A
service-role call carries neither concept. Any Storage-RLS design must be built around
`auth.uid()`, which forces the caller-JWT question addressed in §3, Option B.

### 1.4 Current identity/tenant architecture, verified

- **Authentication:** Supabase Auth is wired (`SupabaseJWKSProvider`); the frontend authenticates
  directly against Supabase and presents the resulting JWT to this backend.
- **`sub` → internal user:** `identity_users.identity_subject` (migration `0013`) stores the IdP's
  `sub` claim verbatim — for a Supabase-issued token, exactly what `auth.uid()` returns inside
  Supabase's own Postgres functions. This mapping already exists; no new column is required.
- **Tenant membership:** one `tenant_id` column on `identity_users`, foreign-keyed to `tenants`
  (migration `0005`, ADR-010).
- **Database/project separation — unresolved:** `Settings.database_url` and
  `Settings.supabase_project_url` are independently configured. `evidence_bucket.sql` states that
  no live Supabase project exists in this implementation environment. **Whether Storage's
  `storage.objects` and the application's `identity_users`/`tenants` tables will share one
  database in the real pilot deployment is not established by anything in this repository.** This
  fact governs §10.4 below and must not be treated as settled in either direction.

### 1.5 Evidence key convention

`evidence/{tenant_id}/{parcel_id}/{uuid}` — server-generated in full; the original filename never
reaches the key. Retained unmodified (§8).

---

## 2. Problem statement

What credential and enforcement model should a server-side LandVault Storage adapter use for
ordinary (non-WORM) Evidence storage, such that Article XI §1's two-layer tenant-isolation
discipline is honestly satisfied, or its absence is an explicitly governed, self-expiring exception
under Article IX §3 — never an unexamined default?

---

## 3. Options considered

### Option A — Trusted backend persistence boundary (service role)

FastAPI's PDP/PEP/`EvidenceService` authorizes every operation before Storage is ever called;
Storage is reached with `SUPABASE_SERVICE_ROLE_KEY` against a bucket with zero
`anon`/`authenticated` policy. This is PR #22's current implementation.

**Benefits:** simplest to reason about and test now; no browser-to-Storage code path exists; no
tenant data enters any JWT; object keys are entirely server-controlled.

**Risks, stated without euphemism:** the service-role credential's blast radius is the entire
bucket, for every tenant, with zero policy backstop; a defect in `EvidenceService`/
`evidence_router.py`'s authorization checks, or in object-key construction, is caught by nothing
downstream. This is a real reduction in defense-in-depth relative to Postgres, not an equivalent
restatement of it (§1.1–§1.2).

### Option B — Dual enforcement with the caller's own Supabase JWT

FastAPI authorizes as today, then calls Storage using the caller's own verified Supabase access
token (forwarded server-side, never browser-to-Storage) instead of the service-role key. Storage's
native RLS independently evaluates the call via `auth.uid()`.

**Feasibility, investigated, not assumed:**

- `auth.uid()` reliably equals `identity_users.identity_subject` for a Supabase-authenticated
  caller (§1.4) — no new mapping required.
- A `SECURITY DEFINER` SQL function with a pinned `search_path`, reading `identity_users`/
  `tenants` directly, is a supported, documented mechanism for a `storage.objects` policy to
  validate an object key's `{tenant_id}` segment against LandVault's own authoritative tables —
  never against a JWT claim.
- **Hard precondition, unresolved (§1.4):** requires `storage.objects` and
  `identity_users`/`tenants` to share one database/project. This option cannot be built or tested
  until that is confirmed in a real environment — see §10.4 for how that determination is made and
  what follows from either answer.

**Risks:** a second enforcement surface must stay in sync with PDP/PEP's tenant semantics — bounded
by keeping the function to one narrow tenant-and-recognized-governance-role check, never a
reimplementation of PDP logic (§10.8); forwarding a per-request caller JWT requires real
construction changes (`evidence/dependencies.py`), not a config flag; stale-identity edge cases
require their own tests (§11).

### Option C — Signed, short-lived scoped URLs

**Rejected for this scope:** no browser-direct-Storage consumer exists or is being added in
IMVP-5. Without one, a signed URL the backend itself immediately redeems is Option A with added
indirection. Reconsider only if a signed-URL download flow is separately, explicitly scoped —
which is itself gated by §10.6.2 below.

### Option 3 — Custom Supabase JWT tenant claim

**Rejected, with justification:**

1. Conflicts with Article X's requirement that delegated authority be "re-resolved fresh on every
   request, never cached" — a JWT claim is stale until token refresh.
2. Conflicts with ADR-004's treatment of LandVault's own Postgres as the authorization-attribute
   source of record, refreshed per request.
3. Closes no feasibility gap Option B's database-lookup path doesn't already close without it.

Custom JWT tenant/role claims are not adopted. No future slice may introduce them for tenant or
role data without a new ADR carrying a materially different justification than convenience.

---

## 4. Privileged / governance cross-tenant access

Under Option A (pilot), no special case is needed — the service-role key already has unconditional
reach, and PDP/PEP already permits governance roles to act across tenants where ADR-011/ADR-015
already grant that. Under Option B (the future dual-enforcement path, §10.5), the same narrow
`SECURITY DEFINER` function that performs the ordinary tenant-match check gets one additional
disjunct recognizing governance/`super_admin` roles — mirroring exactly how `app.is_super_admin`
is a second disjunct in every existing Postgres RLS policy. **This is not solved, now or in the
future, by embedding roles or tenant scope in a JWT claim** — that path is foreclosed by §3,
Option 3, for both the ordinary and the privileged case alike. Any future dual-enforcement design
must demonstrate it does not weaken ordinary tenant protection to accommodate the privileged case.

---

## 5. Threat and failure containment matrix

| Threat | Option A (service role) | Option B (caller JWT + Storage RLS) |
|---|---|---|
| Compromised browser token | No exposure — browser never talks to Storage | Bounded to that user's own tenant by Storage RLS |
| Compromised backend service credential | Full-bucket, all-tenant exposure — no backstop | Removed from the ordinary request path; a retained admin-only service key still carries this risk for its narrower use |
| FastAPI authorization bug (wrong tenant/parcel check) | **Not caught** | **Caught** by independent Storage RLS |
| Storage policy bug (over-broad predicate) | N/A — no policy exists | Live risk; mitigated by keeping the function to one narrow, reviewed check |
| Object-key construction bug | **Not caught** | **Caught** |
| Cross-tenant object-ID guessing | Blocked only by PDP/PEP having already denied the request | Blocked twice |
| Stale tenant membership | Bounded by `context_hydration.py`'s existing no-cache discipline | Same, plus a second, independently-timed lookup |
| Stale privileged role | Same as above | Same, plus the governance branch in §4/§10.8 — fails closed if role match is missing |
| Direct Storage API attempt (bypassing FastAPI) | Denied unconditionally — no `anon`/`authenticated` policy exists | Denied unless the caller holds a valid Supabase JWT for an entitled principal |
| Accidental public bucket exposure | Private bucket, no policy grants access regardless | Same baseline, plus RLS as a second control if the bucket flag were ever flipped |

**Only Option B offers independent failure containment.** Option A's private-bucket configuration
defends against an external attacker and accidental public exposure, but supplies **zero**
containment against a defect in this backend's own authorization or key-construction logic.

---

## 6. Least privilege

No narrower first-class server-side Storage credential is offered by the currently-governed
platform than the service-role key — Supabase does not provide a bucket- or prefix-scoped service
credential as a distinct type. The only narrower mechanism available is Option B's use of the
caller's own already-scoped JWT in place of a broad service credential. This ADR records that
absence rather than inventing a credential type Supabase does not offer.

---

## 7. Relationship to existing ADRs — reconfirmed

- **ADR-004** remains authoritative for authorization attributes. Neither option moves
  authorization *authority* into a JWT claim or Storage-policy metadata. Option B's Storage-level
  check reads LandVault's own authoritative tables directly — enforcement based on authoritative
  database data, not duplication of authority and not a change to ADR-004. Option 3 (JWT tenant
  claims) is the one path that *would* be a genuine change, and it is rejected precisely for that
  reason (§3).
- **ADR-025** remains authoritative for Supabase platform/provider selection. **This ADR is an
  extension/clarification of ADR-025 E3 — it fills the previously-undefined Storage authorization
  model E3 left open. It is not, and must not be cited as, evidence that ADR-025 already made this
  decision.** No other section of ADR-025 is reopened.
- **ADR-026** remains authoritative for Evidence domain semantics. `EvidenceRecord`'s shape,
  `storage_key`/`worm_grade` fields, and the `StoragePort.put`-before-persist ordering are consumed
  as-is; this ADR governs how the adapter reaches Storage, not what the aggregate stores.
- **ADR-021** remains Proposed, unaffected by this ADR in either direction.
- **B5.4+ (WORM, sealing, R2, retention, legal hold, break-glass)** remains entirely untouched,
  undecided, and unimplied by this ADR.

---

## 8. Object keys

`evidence/{tenant_id}/{parcel_id}/{uuid}` is retained under either option:

- generated entirely server-side, from `ExecutionContext.tenant_id` and `EvidenceRecord.evidence_id`;
- `tenant_id` sourced from the authoritative, PDP/PEP-verified `ExecutionContext`, never a request
  body/query parameter;
- `parcel_id` only reaches key construction after `EvidenceService`'s existing parcel-authorization
  check;
- the original filename never controls any path segment;
- no traversal is possible — every segment is a UUID or an already-validated identifier;
- the key alone is never treated as evidence of ownership — `EvidenceRecord`'s own Postgres fields
  remain authoritative.

---

## 9. Decision criteria — scoring (0–10, higher is better except where noted)

| Criterion | Option A (pilot) | Option B (future gate) |
|---|---|---|
| Tenant isolation | 5 | 9 |
| Defense in depth | 3 | 8 |
| Least privilege | 3 | 7 |
| Alignment with ADR-004 | 9 | 8 |
| Alignment with ADR-025 | 9 | 9 |
| Operational simplicity | 9 | 5 |
| Credential blast radius (lower risk scores higher) | 3 | 7 |
| Policy-drift risk (lower risk scores higher) | 9 | 6 |
| Auditability | 6 | 8 |
| Testability | 6 | 7 once buildable; 0 today |
| Pilot feasibility | 9 | 3 — blocked on §1.4's unverified precondition |
| Production scalability | 4 | 8 |
| Governance clarity | 6 | 8 once §10.4's determination is made |

Not mechanically resolved by total. Option B outscores Option A on every isolation-relevant
criterion but cannot be built or tested today. The decision below sequences both rather than
picking one to the exclusion of the other, and binds the sequencing to explicit, expiring
conditions rather than an open-ended "later."

---

## 10. Decision

### 10.0 Current-state truth (stated plainly, per Governance's review)

Under the pilot service-role model:

- **FastAPI's PDP/PEP is the only tenant authorization boundary in effect.** There is no second
  boundary for Evidence Storage.
- **Supabase Storage RLS is bypassed**, unconditionally, by the service-role credential — not
  "satisfied," not "mirrored," bypassed.
- **Storage provides no independent tenant authorization of any kind.**
- **Server-generated object keys are a security control** (they eliminate traversal, caller-chosen
  collisions, and enumeration-by-construction) **but they are not a second authorization layer** —
  a key being well-formed says nothing about whether the request that produced it was authorized;
  that determination was already made, once, by PDP/PEP.
- This is a **deliberate, accepted reduction in defense-in-depth** for the bounded pilot, relative
  to Postgres's PDP/PEP-plus-RLS arrangement. **The two are not equivalent and must never be
  described as equivalent** in code comments, PR descriptions, or future documentation.

### 10.1 Pilot decision and single-tenant boundary

**The service-role Storage model is authorized only while every one of the following remains
true, continuously, not merely at the moment of initial approval:**

1. LandVault is operating the bounded Ehime Mbano pilot only;
2. exactly one tenant is onboarded to Evidence Storage;
3. all Evidence Storage operations pass through FastAPI — no other caller exists;
4. there is no browser/client-direct Storage access of any kind;
5. the bucket remains private, with no `anon`/`authenticated` policy of any kind;
6. B5.4/WORM/sealing/Cloudflare R2/break-glass are not involved in any Evidence Storage operation.

**This authorization expires automatically — without requiring a further governance act to
revoke it — at the earliest of:**

- onboarding a second tenant to Evidence Storage;
- introducing any browser/client-direct Storage operation, including a signed-URL download flow;
- production or commercial deployment beyond the bounded pilot;
- Governance adopting a stronger Storage enforcement architecture (whether Option B or another),
  at which point the stronger architecture supersedes this exception for all operations, not only
  new ones.

Reaching any of these conditions does not, by itself, authorize continuing on the service-role
model "just this once" — it triggers the corresponding hard gate in §10.6, before which no further
Evidence Storage growth may proceed.

### 10.2 Mandatory compensating controls (pilot)

At minimum, and required before PR #22 merges:

- `SUPABASE_SERVICE_ROLE_KEY` server-side only; never bundled into any frontend artifact; never
  committed to Git in any form; never logged; never included in an exception message or audit
  record (already true in the adapter — made an explicit, tested invariant);
- private bucket; no `anon`/`authenticated` policy of any kind on the Evidence bucket;
- no direct client/browser Storage access under any code path;
- every Evidence Storage operation authorized by LandVault's PDP/PEP and `EvidenceService`'s
  creator-or-governance/tenant-scope check **before** the adapter is invoked;
- tenant derived only from the verified `ExecutionContext`, never from request input;
- parcel access checked before any Storage operation;
- server-generated object keys only (§8); no caller-supplied authoritative Storage key, ever;
- application-layer cross-tenant negative tests (§11) proving the boundary that actually exists;
- audit event attribution for every upload/list action (already emitted via kernel `audit()`,
  ADR-007 — retained, not new);
- a documented secret-rotation and revocation runbook for the service-role key (§12);
- a documented incident-response procedure for suspected service-role key exposure — specifically:
  immediate rotation, review of Storage access logs for the exposure window, and a determination
  of whether any cross-tenant read/write occurred, recorded as a security-incident record per the
  same discipline ADR-007 decision 5 already requires for break-glass access.

**Additional control this review identifies as constitutionally motivated, not on the original
list:** a fixed, recorded point at which the §10.1 boundary conditions are re-attested — not a
one-time approval treated as standing indefinitely. Article IX §3's "no exception inherits another
exception's justification" implies an exception must be re-justified, not merely re-discovered to
still apply, at each significant programme milestone (at minimum, before any B5.4+ slice begins
and at any Governance review of pilot status). This closes the gap between "the conditions happen
to still hold" and "someone has actually checked."

### 10.3 Absence of Storage tenant RLS during pilot

Restated for the record: no Storage-level tenant enforcement of any kind exists during the pilot
(§10.0). This is not a gap to be silently tolerated — it is the named, bounded, expiring exception
this ADR governs.

### 10.4 Shared-database verification requirement — a reassessment trigger, not a migration switch

Confirming whether `storage.objects` and `identity_users`/`tenants` share one database is **not,
by itself, an event that requires or authorizes migrating to Option B.** It is a determination
Governance must make **at the point any §10.6 hard gate is reached**, because it decides which
architecture is even available at that point:

- **If shared database = YES:** Option B (§3, §10.5) becomes buildable. Governance evaluates and,
  if adopted, directs its implementation as the architecture satisfying the hard gate — through
  its own implementation slice and its own test evidence, not merely a restatement of this ADR's
  approval.
- **If shared database = NO:** Option B is **not available**, and this ADR does not claim
  otherwise. Before any §10.6 gate may be crossed, Governance must select a **different**,
  independently-enforced Storage model through its own architecture decision — this ADR does not
  pre-select one, because none has been evaluated against a topology where Storage and application
  data are not co-located. **The determination "shared database = NO" is itself the trigger for
  that fresh architecture decision, not a dead end this ADR leaves unaddressed.**

### 10.5 Future dual-enforcement path, if feasible

If §10.4 resolves YES, Option B (§3) is the pre-authorized shape: forward the caller's verified
Supabase token in place of the service-role key for ordinary calls; add the `SECURITY DEFINER`
tenant-and-governance-role check function and its `storage.objects` policies (§4, §10.8); retain
the service-role key only for narrow operational/admin paths, never the ordinary request path.
Building it still requires its own implementation slice, its own tests (§11), and Governance
confirmation — not a full re-litigation of the model chosen here.

### 10.6 Hard gates

#### 10.6.1 Second-tenant hard gate

**A second tenant must not be enabled for Evidence Storage under the pilot service-role
exception.** This is enforceable as a governance process gate: no tenant-provisioning action that
would grant a second tenant access to Evidence Storage may proceed without a recorded Governance
sign-off confirming, in order:

1. the real Supabase deployment topology has been verified (§10.4);
2. a multi-tenant Storage enforcement architecture has been selected (Option B, or another
   architecture decided under §10.4's NO branch);
3. it has been implemented;
4. cross-tenant isolation has been tested against it (§11);
5. a live rehearsal has been completed against the real deployment, not only a fake/in-memory
   harness;
6. any necessary follow-up ADR has been accepted.

This is testable in the direct sense that each of the six items above is a discrete, checkable
artifact (an ADR, a test run, a rehearsal record, a sign-off) — the gate is satisfied when all six
exist, not by assertion.

#### 10.6.2 Browser/client-direct Storage hard gate

Any future capability introducing a browser/client-direct Storage operation (signed-URL download,
viewer, or otherwise) requires its own governance-gated ADR before implementation, and requires
the dual-enforcement model (or whatever architecture §10.4's NO branch selects) to already be live
— it may not be introduced against the pilot service-role model under any circumstance, since a
browser-reachable code path is precisely the scenario the private-bucket compensating control
(§10.2) exists to foreclose.

#### 10.6.3 Production/commercial deployment hard gate

Deployment beyond the bounded pilot is subject to the identical six-item checklist in §10.6.1,
independent of whether tenant count formally increases at the same moment.

### 10.7 Rejected custom-JWT-tenant-claim model — reconfirmed

Option 3 (§3) remains rejected. No future slice, including any implementation of §10.5, may
introduce tenant or role claims into a Supabase JWT without a new ADR carrying a materially
different justification than convenience.

### 10.8 Privileged-access issue — reconfirmed

Any future dual-enforcement design (§10.5) must account for existing governance/`super_admin`
cross-tenant operations (ADR-011, ADR-015) without weakening ordinary tenant protection, and must
do so through the single narrow `SECURITY DEFINER` function's role-recognition branch (§4) — never
through broad JWT claims, which remain rejected under §10.7 for the privileged case exactly as for
the ordinary case.

---

## 11. Test requirements

Under the pilot service-role model, **Storage itself performs no tenant authorization** — a test
named as though it verifies "Storage-layer" tenant protection would misrepresent what pilot
Storage does. Tests are split by what they actually prove:

**Application authorization tests** (prove the one real boundary — PDP/PEP/`EvidenceService`):

- tenant A cannot upload Evidence to tenant B's parcel;
- tenant A cannot list tenant B's Evidence;
- URL/resource manipulation (parcel-ID substitution, path traversal in supplied metadata) fails;
- an unauthorized operation never reaches the Storage adapter at all, where this is testable at the
  service-call boundary (i.e., assert the adapter's `put`/`get` was not invoked, not merely that
  the HTTP response was a denial).

**Storage adapter tests** (prove what the adapter does and does not do — no tenant-authorization
claim):

- the adapter communicates only with the configured private bucket;
- the adapter never exposes the service-role credential in a log, exception, or response;
- the adapter correctly handles server-generated keys and rejects nothing about their shape it
  shouldn't;
- **the adapter does not claim, and a test explicitly documents that it does not attempt, to
  independently authorize tenants** — this is an invariant test recording an absence, not a gap
  left implicit;
- `put_immutable`/`worm_grade` remain unsupported (`NotImplementedError`), unchanged from current
  behavior.

**No test name or docstring may imply Storage RLS protection exists during the pilot.** A prior
draft of this ADR used the phrase "storage-layer cross-tenant test," which risks exactly that
misreading; it is retired in favor of the two categories above.

---

## 12. Secret rotation

No rotation runbook for `SUPABASE_SERVICE_ROLE_KEY` exists yet. Required as a documentation
deliverable before pilot go-live: rotation cadence, the exact steps to rotate without downtime
(issue new key, update secret store, redeploy, revoke old key), and the incident-response
procedure in §10.2's final bullet for suspected exposure. Not code; tracked as a follow-up
deliverable, not implemented by this ADR.

---

## 13. Effect on PR #22

No `StoragePort`/`SupabaseStorageAdapter` method signature change, and no SQL change to
`evidence_bucket.sql`, is required. Required before merge:

1. Correct `SupabaseStorageAdapter`'s module docstring and `evidence_bucket.sql`'s comment block,
   both of which currently claim parity with Postgres RLS that §1.1–§1.2 show is false. Cite
   ADR-027 and state plainly that Storage has one enforcement layer today, per §10.0.
2. Add the application-authorization and Storage-adapter tests in §11, replacing any test naming
   that would imply Storage-layer tenant protection.
3. Confirm, as a tested invariant, that the service-role key is never logged or exposed (already
   true in behavior; make it explicit).
4. Add the secret-rotation/incident-response runbook reference (§12) before pilot go-live.
5. **Remove the unnecessary `SEALED` case in
   `artifacts/landvault-web/src/components/ui/status-badge.tsx`** — its own comment already states
   IMVP-5 never reaches `SEALED`; dead code for this slice, independent of the Storage decision.

None of the above is implemented by this ADR or by this task.

---

## 14. Non-effect on B5.4/WORM/R2

Explicitly restated: this ADR decides nothing about `seal()`, WORM, Cloudflare R2, retention,
legal hold, or break-glass cross-tenant access (ADR-007 decision 5). Each remains ungoverned
pending its own ADR. §10.1 condition 6 makes B5.4+ non-involvement a standing precondition of the
pilot exception itself, not merely an out-of-scope note.

---

## Consequences

- PR #22 is unblocked to proceed under the §10.1–§10.2 pilot model once §13's required corrections
  and tests are added.
- Three named hard gates (§10.6) govern all future growth beyond the bounded pilot; none may be
  crossed by inference or by a single engineer's judgment that "the conditions probably still
  hold."
- The shared-database question (§10.4) is recorded as an open determination with a defined
  consequence on both branches, not left to resolve itself.
- Custom JWT tenant/role claims (Option 3) are foreclosed absent a new ADR with a materially
  different justification.
- A periodic re-attestation requirement (§10.2) prevents the pilot exception from becoming
  permanent by default.

## Rejected alternatives

- **Custom JWT tenant/role claims (Option 3)** — rejected per §3 and reconfirmed at §10.7.
- **Signed/short-lived scoped URLs (Option C)** — rejected for current scope per §3; gated
  identically to any other browser-direct path under §10.6.2 if reconsidered later.
- **Treating PR #22's original Postgres-RLS analogy as sufficient** — rejected; §1.1–§1.2 and
  §10.0 state the correct, honest comparison.
- **An open-ended "migrate to Option B eventually" without hard gates** — rejected per this
  revision; replaced by §10.1's self-expiring conditions and §10.6's enforceable checklists.

## Approval Gate

This ADR is **ACCEPTED**, ratified by Governance Authority on 2026-09-06 (Ratification Record,
above). It is now the governing architecture for ordinary Evidence Storage authorization and
tenant isolation, in force subject to §10.1's pilot conditions and §10.6's hard gates.
**Ratification does not authorize PR #22 to merge** — §13 lists the remediation still required,
and the ratifying decision (§10, item 10) additionally requires, before merge: live Supabase
Storage rehearsal, real browser acceptance, a passing CI run, formal human approval, and the final
Governance merge gate. Any future amendment to this ADR — including selecting the architecture
required under §10.4's NO branch, or authorizing the §10.5 dual-enforcement design — is itself a
governed act per LV-000 Article VI §2 (amendment, not rewriting), not a silent edit to this text.
