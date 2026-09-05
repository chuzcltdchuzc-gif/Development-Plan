-- Supabase Storage bucket for Evidence (B5 IMVP-5, docs/adr/ADR-025-supabase-platform-baseline.md
-- E3 — "Supabase Storage becomes the primary adapter" for ordinary, non-WORM evidence).
--
-- Repository-managed, reviewable configuration, per Supabase's own documented pattern for
-- declaring buckets and Storage policies as plain SQL against the storage.buckets/storage.objects
-- tables (rather than undocumented manual Dashboard clicks) — this is Supabase's supported IaC
-- approach for Storage, not an unsupported internal-schema hack.
--
-- Run once, against the target Supabase project's SQL editor or migration tooling, by whoever
-- holds the project's admin credentials — this file is NOT wired into backend/migrations'
-- Alembic chain (that chain owns the *application* database schema Registry/Evidence/Identity
-- read and write via app.kernel.db; Supabase Storage's bucket/object tables are a separate,
-- platform-level concern, the same distinction ADR-025 E3 itself draws between "the database
-- engine" and "storage"). No live Supabase project exists in this implementation environment to
-- run this against — see the IMVP-5 implementation report's "live Supabase integration status".
--
-- Security model (see app/contexts/evidence/adapters/supabase_storage.py's own module docstring
-- for the full reasoning): the backend is the ONLY caller of Supabase Storage, authenticating with
-- its own server-side service-role key (SUPABASE_SERVICE_ROLE_KEY) — a service-role request always
-- bypasses Storage's RLS policies by Supabase's own design, exactly as this backend's own Postgres
-- connection (DATABASE_URL) is a privileged application role, not a per-user one. Tenant isolation
-- for Evidence is therefore enforced BEFORE Storage is ever called — by the existing PDP/PEP
-- (require_auth/require_role) and EvidenceService's own creator-or-governance parcel-authorization
-- check (app/contexts/evidence/application/evidence_service.py) — not by a Storage-level RLS
-- policy keyed on tenant_id, which a service-role caller would bypass anyway and which browser
-- clients never have a code path to reach in the first place (no direct browser-to-Storage upload
-- exists in this design — see Preflight Gate B in the IMVP-5 implementation report).
--
-- What this file's policies actually provide (the real, honest "second independent layer",
-- mirroring the role Postgres RLS plays for the database per ADR-025 E2): the bucket is private
-- and grants NO access to the anon/authenticated Supabase roles at all. Even a browser that
-- somehow obtained a valid Supabase session JWT and tried to call Storage directly (bypassing this
-- backend entirely) is denied — only the service_role key this backend alone holds can read or
-- write anything in this bucket.

-- Idempotent: safe to run more than once against the same project.
insert into storage.buckets (id, name, public)
values ('evidence', 'evidence', false)
on conflict (id) do update set public = excluded.public;

-- Explicitly no policies are created for the `anon` or `authenticated` roles on this bucket.
-- Supabase Storage defaults to denying all access to a bucket once Row Level Security is enabled
-- on storage.objects (already the platform default) unless a policy explicitly permits it — the
-- absence of such a policy here is the deliberate control, not an oversight.
--
-- If a future, separately-governed slice ever needs the browser to talk to Storage directly
-- (e.g. a signed-URL download flow), that is a new capability requiring its own authorization
-- design and its own policy added here under its own governance decision — not assumed by this
-- file, and explicitly out of scope for IMVP-5 (Section 27: "No download/viewer expansion").
