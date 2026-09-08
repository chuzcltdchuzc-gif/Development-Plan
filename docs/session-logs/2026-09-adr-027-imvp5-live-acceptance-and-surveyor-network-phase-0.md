# Session Log — ADR-027 Storage Security Governance, PR #22 IMVP-5 Live Acceptance, and Surveyor Network Phase 0

**Type: historical record only. This is not a governance document, not an ADR, not part of the
Constitution, and not part of the Bible volume numbering.** It is a plain narrative account of one
Claude Code conversation, kept so a future reader has context on *why* certain documents and code
changes were produced and in what order — never as evidence of what any document or the codebase
currently says. If anything below conflicts with the actual, current content of any governing
document, any ADR, or the code itself, **those are correct and this log is simply out of date.**
This log is not updated retroactively when things change after the fact; it records what happened
at the time, not what is current now.

**Date range covered:** 2026-09-06 through 2026-09-08.

---

## How this conversation started

The conversation opened mid-stream: PR #22 (`feat/imvp-5-evidence-vertical-slice`) already existed,
implemented and CI-green, but blocked on a governance-authority-style finding that its Supabase
Storage security model had not actually been decided by any accepted architecture document — its
own PR description's claim that ADR-025 E2 already authorized the service-role pattern was, on
inspection, incorrect. Every step from there through PR #22's eventual squash-merge, and the
Surveyor Network Phase 0 work that followed it, proceeded as a long sequence of separately
authorized, separately verified governance-and-implementation passes, each one re-establishing
ground truth (git state, live Supabase state, CI state) directly rather than trusting the previous
step's report — the same discipline named explicitly in the prior session log's §5, continued here
at a larger scale.

## 1. ADR-027 — correcting the Storage security claim

Reading the actual mechanism rather than accepting PR #22's own framing found a real, factual error:
Postgres RLS in this codebase is a same-connection backstop (the backend's own trusted connection
sets `app.tenant_id` before every query); Supabase Storage's native RLS is a completely different
mechanism keyed on `auth.uid()`, populated only when a caller presents their own Supabase JWT
directly to Storage. The two are not the same pattern applied twice. `SupabaseStorageAdapter`
authenticated with the service-role key exclusively, which unconditionally bypasses Storage RLS —
meaning Storage had **one** enforcement layer (PDP/PEP), not two, unlike Postgres. This was drafted
as ADR-027 (verified as the correct next number by reading `docs/adr/` directly — ADR-020 is
deliberately, permanently vacant, so a naive "highest + 1" allocator would have collided with it).
The draft recommended a staged model: the pilot proceeds on the service-role credential as an
explicitly named, self-expiring exception, with a pre-authorized future dual-enforcement
architecture (forwarding the caller's own JWT to Storage, with a `SECURITY DEFINER` database
function checking tenant membership) gated behind three hard gates — a second tenant, any
browser-direct Storage path, or production deployment.

## 2. ADR-027 ratification-readiness review and revision

A follow-up governance pass tightened the draft rather than accepting it as final: the pilot
exception needed to be stated as a set of *continuously-true* conditions with an *automatic*
expiration, not a one-time approval; a planned test description ("a Storage-layer cross-tenant
test") risked implying Storage-level tenant protection that does not exist during the pilot and was
renamed to separate "application authorization tests" from "Storage adapter tests"; a periodic
re-attestation requirement and an incident-response procedure for suspected credential exposure
were added, since neither had been in the original draft. The revised ADR was judged consistent and
ready for ratification.

## 3. ADR-027 ratified, merged to main (PR #23)

Governance Authority ratified the revised text directly. The ADR file was updated in place with a
Ratification Record (no separate GD number existed yet for this kind of act at the time), then
committed on a fresh branch cut from `origin/main` — never from PR #22's own branch — specifically
to avoid a documentation change landing inside an unrelated feature PR. PR #23 merged as `1ff4bc9`,
carrying only the ADR itself, its supporting architecture report, and a short `CLAUDE.md` pointer;
zero application code was touched, verified by diffing the merge commit against its parent under
`backend/`, `artifacts/`, `lib/`, and `infra/` and finding nothing.

## 4. PR #22 brought into ADR-027 compliance

With the ADR ratified, PR #22 itself needed remediation, not merely a documentation note: the
adapter's own module docstring and `infra/supabase/evidence_bucket.sql`'s comments repeated the same
now-corrected two-layer claim, and needed rewriting to state the single-layer pilot truth plainly.
A new test (`test_rejected_cross_tenant_upload_never_invokes_storage_adapter`) proved, rather than
merely asserted, that a denied request never reaches `StoragePort` at all. Two new adapter tests
documented the invariant that the adapter performs no tenant validation of its own and never accepts
a per-call caller token. Two new operational documents were added —
`EVIDENCE_STORAGE_CREDENTIAL_RUNBOOK.md` and `EVIDENCE_STORAGE_PILOT_BOUNDARY_CHECKLIST.md` — and the
unreachable `SEALED` case in `StatusBadge` (IMVP-5 never calls `seal()`) was removed. 293 backend
tests passed; the commit landed as `4055aab`.

## 5. Getting the Supabase credential header logic actually right — two attempts

Preparing for live rehearsal, a preflight check against a real (though at the time placeholder)
credential produced `Invalid Compact JWS` from Supabase Storage. Research into Supabase's current
API-key system (`sb_secret_...`, replacing the legacy JWT-form `service_role` key) found the
platform's own documentation: send the new key format via `apikey`, never `Authorization: Bearer`,
since a non-JWT value there fails JWT parsing outright. The adapter was changed to send `apikey`
unconditionally and add `Authorization: Bearer` only for a JWT-shaped credential (commit `a197118`).
**This first fix turned out to be wrong**, discovered only once a real credential existed: a live
probe of `/storage/v1/object/list/{bucket}` — the actual endpoint the adapter's `list_keys` calls,
as opposed to the unrelated bucket-management endpoint used for the earlier diagnostic — showed
Supabase's own object-level routes reject an `apikey`-only request (`headers must have required
property 'authorization'`) and accept the current secret key in `Authorization` just fine when both
headers carry it. The general "apikey only" platform guidance describes PostgREST's gateway check,
not Storage's own separate request-schema validation. The adapter was corrected a second time to
send both headers unconditionally, with the same value in each, for either credential format
(`1eb958a`) — with new tests replacing the ones that had encoded the now-known-wrong conditional
behavior.

## 6. Live rehearsal — three real blockers found and cleared in sequence

**Attempt one** stopped at preflight: the locally configured `SUPABASE_SERVICE_ROLE_KEY` was a
placeholder, and the local Postgres was one migration behind the code's expectation (`0012` vs. the
required `0013`, the `keycloak_subject`→`identity_subject` rename) — neither fixable without
credentials this session correctly did not hold (no `MIGRATIONS_DATABASE_URL`, no real Supabase key).
**Attempt two**, after the user reported both fixed, found the real database was actually on a
*different* local Postgres container than the one checked the first time (the user had repointed
`DATABASE_URL` to `landvault-imvp3-test-pg` on port 5433, not the docker-compose Postgres on 5432)
— once the correct container was checked, migration `0013` was confirmed present. The Storage
credential, however, still failed the same `Invalid Compact JWS` probe, leading to a classification
of "invalid" — **which was itself wrong**, corrected in the very next turn once the user
independently proved the key valid via `GET /rest/v1/` returning `200`, and once the real culprit
was identified as §5's header-logic bug rather than the credential itself. **Attempt three**, run
against the corrected adapter, succeeded: the real bucket (created by applying
`infra/supabase/evidence_bucket.sql` for the first time against a live project) was confirmed to
exist and be private, and the environment was declared ready.

## 7. Real browser acceptance and independent proof

The user performed the actual journey — real Supabase login, parcel `LV-NG-000004`, one small JPEG
upload. Rather than trust the UI's `HASHED` display, the result was independently re-derived:
the Evidence row (`2c410a64-3d24-48d3-ba33-c351e603e566`) was queried directly from Postgres; the
real Storage object was fetched a second time using the backend's own credential and its bytes were
independently re-hashed outside the application entirely, matching the persisted SHA-256 exactly;
the backend's own request log showed the real outbound `httpx` calls to Supabase Storage
(`POST`/`GET`, both `200`) with timestamps consistent with the audit log's `evidence.uploaded`/
`evidence.hashed` entries; and the backend's HTTP access log showed the real `POST → 201`/`GET →
200` from the browser itself, with no `/v1/v1`, no Vite fallback, and no browser-to-Supabase call of
any kind.

## 8. Merge gates, a branch-sync detour, and the squash merge

A first "final merge gate" pass found everything green except one thing GitHub itself reported:
`mergeable_state: behind` — PR #22's branch had never absorbed ADR-027's own merge to `main`
(`1ff4bc9`), and the repository's branch protection required a strict, up-to-date status check.
Two small, precisely identified stray files (a captured `less` help screen and a captured
grep-transcript, both confirmed to carry no secret) were deleted by their exact names before the
sync, `git status` confirmed empty, then `origin/main` was merged into the feature branch with a
normal merge commit (no rebase, no force-push) — landing at `783fa5a`, verified byte-for-byte
identical to the pre-sync tested head under every runtime path. CI re-ran green, a fresh human
approval landed on the new head, and a second full merge-gate pass confirmed everything satisfied.
PR #22 was squash-merged as `5b8cdb0`; a post-merge pass re-ran the full test suite directly against
the new `main` tip and reconfirmed every finding.

## 9. Surveyor Professional Network — reality audit and blueprint

A large, code-only, no-implementation architecture task followed: a full reality audit of `main`
found the entire Surveyor Professional Network domain consists of five RBAC role strings and one
undifferentiated `EvidenceRecord.uploaded_by` field — nothing else exists, despite two pre-existing,
unopened planning documents (`MARKETPLACE_DISCOVERY_AND_PLANNING.md`,
`PARTNER_PROGRAMME_STRATEGY.md`) already naming most of the candidate concepts. The resulting
blueprint (`SURVEYOR_PROFESSIONAL_NETWORK_AND_COMMERCIAL_ARCHITECTURE.md`) proposed an actor model,
a Job/Assignment aggregate shape, terminology corrections ("Surveyor Trust Index" rejected in favor
of "Professional Performance Index"; "Resolved evidence conflict" rejected in favor of "Evidence
discrepancy professionally documented"), a fraud red-team table, and a pre-mortem — all kept
uncommitted, per instruction, pending governance review.

## 10. Phase 0 reconciliation and GD-008

A second pass reconciled that blueprint against the two pre-existing planning documents and answered
the specific open questions each had left unresolved: Marketplace decomposes into two contexts
(Marketplace, Partner), not the full surveyed set; a surveying practice or sole professional is a
`Tenant`, unchanged, with Partner status modeled as a referencing accreditation record rather than a
new tenant subtype; Job and Assignment split into a customer-facing aggregate and a subordinate
lifecycle fact, respectively; and exactly one architecture question — Evidence actor/provenance
attribution (Originated By / Reviewed By / Commissioned By) — was found mature enough for an ADR
now, with everything else blocked on the still-unopened Marketplace/Partner discoveries or on a
named list of Nigerian legal questions. The next Governance Decision number was verified directly
against `LV-000-constitution.md`'s own Article XVI log (GD-007 was the highest recorded) rather than
assumed, giving **GD-008**. Governance Authority ratified GD-008 with several sharpened refinements
(a labeled "Important qualification" making explicit that the two-context finding does not preempt
Marketplace's own formal discovery; a four-part tenant formulation), which were folded back into the
document to match the ratified text exactly.

## 11. Landing the Phase 0 record on main (PR #24)

The four resulting documents — the blueprint, the reconciliation, GD-008 itself, and its
pre-ratification readiness report — were committed on a fresh branch cut from `main` (`1fbfda8`)
and opened as PR #24, left open pending review rather than merged, consistent with every prior
documentation change in this conversation landing through its own reviewed PR rather than a direct
push.

## What remained open at the end of this conversation

- PR #24 (the Surveyor Network Phase 0 record) is open, not merged.
- ADR-028 (Evidence actor/provenance attribution) is authorized to be drafted by GD-008, but drafting
  had not begun as of the end of this conversation.
- Neither `MARKETPLACE_DISCOVERY_AND_PLANNING.md`'s nor `PARTNER_PROGRAMME_STRATEGY.md`'s own Phase
  0 Approval Gate has been opened — GD-008 explicitly does not close either.
- The full Nigerian legal/professional-body checklist GD-008 §10 names (SURCON licensing, copyright
  default, escrow legality, NDPR, and the rest) had not been referred to counsel.
- The future dual-enforcement Storage architecture ADR-027 names as its mandatory production gate
  (forwarding the caller's own JWT, a `SECURITY DEFINER` tenant-check function) remains unbuilt,
  correctly, since none of its triggering conditions (a second tenant, browser-direct Storage,
  production deployment) had occurred.
- B5.4 (WORM sealing) and everything after it in the Evidence roadmap remain unauthorized and
  untouched.
