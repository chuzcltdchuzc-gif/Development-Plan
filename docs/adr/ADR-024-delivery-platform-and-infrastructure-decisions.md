# ADR-024 — Delivery Platform & Infrastructure Decisions

**Status:** Proposed — 2026-07-30. No code has been written under this ADR. It records decisions
already directed by `docs/EXECUTION_PLAN.md` §4.2–§4.4 and §7.2, plus the AWS compute-provider note
that has so far lived only inline in `CLAUDE.md` and §6 step 8; it authorises nothing new.

**Date:** 2026-07-30

**Scope:** The architectural decisions governing the delivery platform's infrastructure surface —
the `StoragePort` abstraction and its Cloudflare R2 pilot adapter, WORM/retention grading, the
Keycloak identity provider, Paystack payments for pilot one, the AWS compute/cloud provider
decision, and the secrets manager (undecided). For each, this ADR states what was decided, the
abstraction boundary it sits behind (if any), the alternatives considered, and what remains open.
**This is a decision record, not a cloud-service inventory** — it does not attempt to enumerate
every AWS service that might eventually be used, only the ones a delivery decision has actually
been made about, or explicitly deferred. Out of scope: the Keycloak `start-dev`→production-mode
migration, which is tracked separately as infrastructure-hardening work, not decided or performed
here (see "D2" below for why that boundary is deliberate).

**Constitutional anchors:** Article VII §2–§4 (WORM grade declared; escalation without code change;
demonstrable integrity); Article X §3 (the single authorisation path); Article X §5–§6 (ports;
seams declared); Article XI §2–§4 (observed not assumed; reversible; governed dependencies).

## Context

`docs/EXECUTION_PLAN.md` §4.2–§4.4 name storage, identity and payments as "binding delivery
decisions... to be recorded as an ADR" (§11.1), listing this ADR's working title as "Delivery
Platform Decisions." Separately, the compute/cloud provider (AWS) has been decided but has existed
only as an inline note in `CLAUDE.md` and `EXECUTION_PLAN.md` §6 step 8 — GD-006 regularised the
fact that a confirming note was added to those already-ratified instruments after ratification, but
GD-006's own text is explicit that it "does not itself authorise... any infrastructure change" —
the AWS decision itself has never had a citable instrument. This ADR is that instrument, and — per
this session's direction — is scoped broader than "AWS-specific": it is the one citable place for
every delivery-platform infrastructure decision named in §4.2–§4.4, framed around architectural
rationale, abstraction boundaries, replacement criteria and governance constraints, not a service
inventory.

## Decision

### D1 — Object storage: `StoragePort`, Cloudflare R2 pilot adapter, WORM grading

A provider-agnostic **`StoragePort`** (`put` / `get` / `list`, plus `putImmutable(retention)` and
`wormGrade()`) is the only way any bounded context touches object storage (Article X §5 — **no
bounded context calls a storage SDK directly**). This is the identical "port before adapter"
doctrine `docs/adr/ADR-016-geometry-port-boundary-spatial-integration.md` already established for
`GeometryPort` — cited here as precedent for the discipline, not because the two ports share a
contract.

**Cloudflare R2** is the pilot default adapter. `wormGrade()` returns one of two values:

| Backend | Grade | Meaning |
|---|---|---|
| Cloudflare R2 Bucket Locks | `governance` | Retention revocable by a privileged administrator |
| S3 Object Lock (compliance mode), Azure, GCS, MinIO | `compliance` | Irrevocable retention, with legal hold |

**Replacement criteria:** escalating from `governance` to `compliance` grade happens by swapping
the adapter behind `StoragePort`, without a code change to any calling context (Article VII §3).
The trigger for that escalation — the required WORM grade for the actual pilot jurisdiction and
data-residency requirement — is confirmed with the pilot partner and counsel, and remains an open
decision tracked at `docs/EXECUTION_PLAN.md` §10 ("Data residency and required WORM grade," due
Phase 3). This ADR does not resolve it early.

**Current implementation status, verified, not assumed:** no `StoragePort` code, R2 adapter, or
`wormGrade` implementation exists anywhere in `backend/` as of this ADR (checked by search; zero
matches). This ADR records the decision ahead of the implementation, exactly as ADR-023 recorded
its schema decision before any migration existed.

**Alternatives considered:**
- Call R2's S3-compatible SDK directly from each context that needs storage, with no port —
  rejected: violates Article X §5 and makes the `governance`→`compliance` escalation a rewrite
  instead of an adapter swap.
- Commit to S3 Object Lock as the only backend now, skipping R2 — rejected: `EXECUTION_PLAN.md`
  §4.2 names R2 as the pilot default, and deciding the compliance-grade backend before the
  data-residency requirement is confirmed would be arguing ahead of the evidence.

### D2 — Identity provider: Keycloak, confirmed

`docs/adr/ADR-004-authentication-authorisation-model.md` left Keycloak vs. Auth0 as an explicit
open sub-decision, recommending Keycloak (self-hosted data residency for government/citizen PII;
no per-monthly-active-user pricing at pilot scale) with Auth0 as a faster-to-bootstrap fallback.
`docs/EXECUTION_PLAN.md` §4.3 states "Keycloak, confirmed." **This ADR is the citable record of
that resolution** — it supersedes ADR-004 on this one point only. ADR-004's PDP/PEP/PIP
authorization design, its fail-closed evaluation, and its single-authorization-path guarantee
(Article X §3) are entirely unchanged and continue to govern regardless of which IdP backs
authentication.

The realm is exported as code at `infra/keycloak/realm-landvault.json` (first committed at
`72dcc85`; correctness of that export is a separate, evidentiary concern being resolved in its own
commit and is not re-litigated here).

**Governance constraint, stated but not performed here:** `EXECUTION_PLAN.md` §4.3 requires
production mode — database-backed, TLS, explicit hostname — before staging; dev mode must never
reach staging. **This ADR records that requirement; it does not carry out the `start-dev`-to-
production migration.** That migration is tracked as a separate infrastructure-hardening task, by
this session's explicit direction, so that a platform *decision* (which IdP, on what terms) stays
separate from an infrastructure *hardening* activity (how the currently-decided IdP is deployed
safely). Conflating the two would make this ADR a checklist of deployment steps rather than a
decision record.

**Alternatives considered:** Auth0 — the fallback ADR-004 already named; not re-argued here since
ADR-004's reasoning stands and nothing has changed it.

### D3 — Payments: Paystack only for pilot one, narrowing ADR-006

`docs/adr/ADR-006-payment-architecture.md` decided **both** Paystack (Nigeria-first) and Stripe
(diaspora/international). `docs/EXECUTION_PLAN.md` §4.4 narrows this for delivery: "**Paystack**
only for pilot one. Stripe deferred; deferral is recorded, not assumed." **This ADR records that
narrowing as a citable decision, superseding ADR-006 on scope-for-pilot-one only.** ADR-006's
atomic-ledger function, idempotency-key discipline, and webhook-signature-verification design are
unchanged and provider-agnostic already — nothing about narrowing to one active provider requires
touching that architecture.

**Replacement criteria:** re-enabling Stripe for a later pilot or market requires no ledger
redesign — only re-enabling the already-audited Stripe webhook path behind the same ledger
function ADR-006 already specified. No trigger date or condition for that re-enablement is recorded
here; it remains genuinely deferred, not scheduled.

**Current implementation status, verified, not assumed:** no Paystack integration code exists
anywhere in this repository as of this ADR (checked by search; zero matches). This decision
precedes its implementation.

**Alternatives considered:** none re-litigated here — ADR-006 already weighed Paystack vs. Stripe
at the architecture level; this ADR only narrows *which one is active for pilot one*, a delivery
scoping decision, not a re-opening of ADR-006's provider architecture.

### D4 — Compute/cloud provider: AWS, an interim, low-stakes decision

`infra/terraform/versions.tf` declares the `hashicorp/aws` provider (region `eu-west-2` default,
provider block only — **no resources**). Decided 2026-07-30; until this ADR, recorded only as an
inline note in `CLAUDE.md` and `EXECUTION_PLAN.md` §6 step 8, and regularised by GD-006 strictly as
an observation that the note exists — GD-006 does not itself ratify the decision.

**Why this decision is low-stakes as made:** `EXECUTION_PLAN.md` §6 step 8 itself says the choice
"is not urgent and should not be rushed," because storage is already decoupled behind `StoragePort`
(D1) — the compute provider has no bearing on where evidence is sealed or how WORM grading works.
Verified: no resource beyond the bare provider block is declared, so nothing in this codebase
currently depends on an AWS-specific API or service.

**Abstraction boundary:** none is introduced at the compute layer by this ADR, because there is no
compute-coupled code yet to abstract. If and when code is written that depends on a specific
managed service (a queue, a managed database offering, a named AWS SDK call), **that code should
sit behind its own port**, following the identical "no bounded context calls a cloud SDK directly"
discipline as D1 — this ADR deliberately does not invent a speculative `ComputePort` now, absent
any concrete resource to abstract (rule of three).

**Replacement criteria:** with zero resources provisioned, changing the compute provider today
costs only a Terraform provider-block edit. This changes the moment real resources are declared —
at that point, this ADR should be **amended, not silently edited**, to record what was provisioned
and what switching would then cost.

**Alternatives considered:** none formally evaluated — recorded honestly, per `CLAUDE.md`'s own
note, as an administrative placeholder decision rather than a reasoned provider comparison. A
GCP/Azure/on-prem comparison was not performed and this ADR does not manufacture one after the
fact.

### D5 — Secrets manager: undecided

`EXECUTION_PLAN.md` §4.3 requires "secrets in a manager" before Keycloak reaches production. **No
specific secrets manager has been chosen.** This is recorded as **undecided**, not defaulted: if
AWS remains the compute provider when this is decided, AWS Secrets Manager is an obvious candidate,
but that is not a decision this ADR makes, and no rationale is manufactured to make this section
look more finished than the actual state of the decision.

## Alternatives considered (cross-cutting)

A single narrative "cloud architecture" ADR naming every service touched, in the style of a
service inventory, was considered and rejected in favour of the per-surface structure above:
storage, identity, payments and compute each have independent abstraction boundaries and
independent replacement criteria (Article X §5–§6), and collapsing them into one inventory would
obscure exactly the ports-and-adapters distinctions this ADR exists to make explicit.

## Relationship to the frozen baseline

- **ADR-004** — the open Keycloak-vs-Auth0 sub-decision is resolved (Keycloak). Every other part
  of ADR-004 — the PDP/PEP/PIP design, the single-authorization-path guarantee, the role-hierarchy
  check — is unchanged.
- **ADR-006** — the Paystack/Stripe decision is narrowed to Paystack-only for pilot one. The
  atomic ledger, idempotency and webhook-verification architecture is unchanged and remains
  provider-agnostic.
- **ADR-009 (B1 Platform Freeze)** — unaffected; this ADR extends the infrastructure surface those
  frozen decisions already run on top of, and touches none of them.
- **ADR-016** — `StoragePort` follows the same "port before adapter" doctrine ADR-016 established
  for `GeometryPort`. ADR-016 itself is untouched.
- No frozen decision requires amendment beyond the two narrowings above (ADR-004, ADR-006), both
  of which `docs/EXECUTION_PLAN.md` already directed (§4.3, §4.4) rather than positions this ADR
  invents.

## Consequences

- The AWS compute decision becomes a citable decision of record instead of an inline note in
  `CLAUDE.md`/`EXECUTION_PLAN.md` — those documents are updated to point here rather than to carry
  the substance themselves.
- What remains open after this ADR, stated plainly rather than rounded up to resolved: the secrets
  manager (D5, undecided); the required WORM grade and its data-residency driver (Phase 3, per
  `EXECUTION_PLAN.md` §10); the Keycloak `start-dev`-to-production migration (tracked separately,
  as infrastructure hardening, not by this ADR); any Stripe re-enablement timing (deferred, no
  trigger recorded).
- No new authorization model, endpoint, or migration is introduced by this ADR. Nothing here
  changes the acceptance criteria of any other Proposed or Accepted ADR.
