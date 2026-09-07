# Evidence Storage Credential Runbook

**Governed by:** `docs/adr/ADR-027-supabase-storage-authorization-and-tenant-isolation.md`
(Accepted) §10.2 and §12. This runbook is the operational deliverable those sections require; it
decides nothing new and must not be read as amending the ADR. Where this document and the ADR
appear to differ, the ADR governs.

**Scope:** `SUPABASE_SERVICE_ROLE_KEY`, the single credential `SupabaseStorageAdapter`
(`backend/app/contexts/evidence/adapters/supabase_storage.py`) uses to reach Supabase Storage
during the bounded pilot. Does not cover `DATABASE_URL`, Supabase Auth's JWKS configuration, or any
other secret — each has its own operational ownership, unchanged by this document.

**Credential format:** Supabase currently supports two formats for this credential, both carrying
the identical elevated, RLS-bypassing trust role ADR-027 governs
(https://supabase.com/docs/guides/api/api-keys): the current non-JWT **secret key**
(`sb_secret_...`) — preferred for new setups — and the legacy **service_role JWT**, which Supabase
states "remains valid until you disable them." The adapter sends both `apikey` and
`Authorization: Bearer` with the same value for either format — live-verified against Storage's
own object-level routes, which require `Authorization` to be present and accept the current
secret-key format there without treating it as a JWT (see supabase_storage.py's own module
docstring for the full investigation) — no runbook step differs by format; obtain whichever the
project's dashboard currently issues.

This runbook describes procedures against **Supabase's currently-documented, supported project
administration surface** (the project dashboard's API settings, where project API keys are viewed
and, where the platform offers it, rotated). It does not invent a Supabase capability that has not
been verified to exist. If a step below assumes a capability that turns out not to be available in
the target project's Supabase plan/tier, stop and escalate to Governance rather than improvising a
substitute control.

## 1. Routine credential rotation

Performed on a planned schedule or ahead of a known event (e.g., before onboarding beyond the
bounded pilot per ADR-027 §10.6), not only in response to an incident.

1. In the Supabase project dashboard, generate/obtain the new service-role key using the current
   Supabase-supported administrative procedure for that project.
2. Update the value in the backend's secret storage only (`SUPABASE_SERVICE_ROLE_KEY`) — the
   platform secret manager once one is adopted (ADR-025 E5 remains undecided; until then, the
   deployment environment's own secret/environment mechanism, never a file committed to Git).
3. **Never** place the new or old key value in a Git commit, a pull request description, a chat
   message, a log line, or an issue/ticket body.
4. Restart or redeploy the backend so the new value is loaded (`Settings.supabase_service_role_key`
   is read at process start — there is no hot-reload path for this setting).
5. Perform a controlled Storage smoke test: as an authenticated, authorized test user, upload one
   small test Evidence file to a non-production parcel and confirm a `201` response and a
   subsequent `GET` listing showing it `HASHED`. This proves the new credential works before
   declaring rotation complete.
6. Revoke/retire the old key via the same Supabase administrative surface once the smoke test
   passes, per Supabase's current documented process for retiring a superseded key.
7. Record the rotation (date, operator, reason) in the Governance record — not the key value
   itself.

## 2. Suspected service-role key compromise

Treat any of the following as a suspected compromise: the key appears in a log, a committed file,
a screenshot, a support ticket, or any other channel outside the backend's own secret storage; or
Storage activity is observed that this backend did not initiate.

1. **Rotate/revoke immediately** using the same Supabase-supported procedure as §1, steps 1–2 and
   6 — do not wait for a scheduled window.
2. If immediate rotation is not instantly available, and the exposure is severe enough to warrant
   it, suspend Evidence Storage operations at the application layer (the upload/list endpoints can
   be feature-flagged or the deployment paused) until a new credential is in place — a judgment
   call for whoever is on call, escalated to Governance if there is any doubt.
3. Inspect Supabase Storage activity/logs available through the project's own dashboard or API for
   the suspected exposure window, **without printing or transcribing the credential itself**
   anywhere in the investigation record.
4. Confirm the bucket is still configured private, with the `anon`/`authenticated` policy
   configuration in `infra/supabase/evidence_bucket.sql` unchanged and unapplied-to by anyone
   outside this process.
5. Look specifically for object activity outside what this backend's own audit log
   (`evidence.uploaded`/`evidence.hashed` entries, ADR-007) accounts for — any object write/read
   not matching a corresponding audit entry is a signal of unauthorized activity and must be
   escalated.
6. Escalate to Governance/security regardless of whether unauthorized activity is confirmed — the
   exposure itself is reportable, independent of observed impact.
7. Document the incident: what was exposed, how, the exposure window, what was found on
   inspection, and the remediation timeline — again, never the credential value itself.
8. Validate the new credential with the same controlled smoke test as §1 step 5 before declaring
   Evidence Storage operations re-enabled.

## 3. What this runbook does not cover

Bucket-level or prefix-level credential scoping is not offered as a distinct Supabase credential
type today (ADR-027 §6) — this runbook does not describe a narrower-credential procedure because
none currently exists to describe. If Supabase later offers one, this runbook should be revised
alongside a review of whether it changes ADR-027's own least-privilege finding.
