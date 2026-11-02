# Evidence Storage Pilot Boundary — Re-attestation Checklist

**Governed by:** `docs/adr/ADR-027-supabase-storage-authorization-and-tenant-isolation.md`
(Accepted) §10.1, §10.2, and §10.6. This checklist is the operational artifact that ADR-027 §10.2
requires so the pilot exception is periodically re-justified rather than assumed to still hold. It
decides nothing new; where this document and the ADR differ, the ADR governs.

## When to run this checklist

- Before any B5.4+ slice begins.
- At any Governance review of pilot status.
- Before any change that could plausibly affect one of the conditions below (a new deployment
  target, a new tenant-provisioning path, any Storage-adjacent feature work).

## Continuously-true pilot conditions (ADR-027 §10.1)

All six must be re-confirmed true, not merely assumed unchanged since the last check:

- [ ] LandVault is operating the bounded Ehime Mbano pilot only.
- [ ] Exactly one tenant is onboarded to Evidence Storage.
- [ ] All Evidence Storage operations pass through FastAPI — no other caller exists.
- [ ] There is no browser/client-direct Storage access of any kind.
- [ ] The Evidence bucket remains private, with no `anon`/`authenticated` policy of any kind
      (`infra/supabase/evidence_bucket.sql` unchanged in substance since last review).
- [ ] B5.4/WORM/sealing/Cloudflare R2/break-glass are not involved in any Evidence Storage
      operation.

**If any box cannot be checked, the pilot exception has already expired** (ADR-027 §10.1's
automatic-expiration clause) — stop and escalate to Governance before any further Evidence Storage
work proceeds. Re-checking this list is a confirmation exercise, not a request for permission to
continue regardless of the answer.

## Hard gates (ADR-027 §10.6) — confirm none has been silently crossed

### Second-tenant hard gate

A second tenant must not have been enabled for Evidence Storage without all of the following
existing as recorded artifacts:

- [ ] The real Supabase deployment topology has been verified (does `storage.objects` share a
      database with `identity_users`/`tenants`? — ADR-027 §10.4).
- [ ] A multi-tenant Storage enforcement architecture has been selected accordingly.
- [ ] It has been implemented.
- [ ] Cross-tenant isolation has been tested against it.
- [ ] A live rehearsal has been completed against the real deployment.
- [ ] Any necessary follow-up ADR has been accepted.

### Browser/client-direct Storage hard gate

- [ ] No browser/client-direct Storage code path (signed-URL download, viewer, or otherwise) has
      been introduced without its own governance-gated ADR and without the dual-enforcement
      architecture (or ADR-027 §10.4's NO-branch alternative) already being live.

### Production/commercial deployment hard gate

- [ ] Deployment has not moved beyond the bounded pilot without satisfying the identical six-item
      checklist under "Second-tenant hard gate" above.

## Compensating controls still in force (ADR-027 §10.2)

- [ ] `SUPABASE_SERVICE_ROLE_KEY` is server-side only, absent from any frontend build artifact,
      absent from Git history, absent from logs and audit records.
- [ ] PDP/PEP and `EvidenceService`'s creator-or-governance/tenant-scope check run before every
      Storage call — no code path calls `StoragePort` first.
- [ ] Object keys remain server-generated only (`evidence/{tenant_id}/{parcel_id}/{uuid}`).
- [ ] The credential rotation/incident-response runbook
      (`docs/EVIDENCE_STORAGE_CREDENTIAL_RUNBOOK.md`) is current and has not been superseded by an
      undocumented process change.

## Record of this attestation

| Date | Attested by | Result | Notes |
|---|---|---|---|
| 2026-09-06 | ADR-027 remediation (this document's creation) | All conditions true; zero tenants onboarded; no browser-direct path; bucket private; no B5.4 work in progress | Baseline attestation at remediation time, prior to any live Supabase rehearsal |

Add a new row each time this checklist is run. Do not overwrite prior rows.
