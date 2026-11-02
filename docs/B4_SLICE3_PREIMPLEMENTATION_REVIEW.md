# B4 Slice 3 Pre-Implementation Review

**Type:** Architectural review record, **not an ADR.** Documents the pre-Slice-3 governance
review performed against ADR-021, and the package-level coherence check across the Threat Model,
ADR-021, ADR-022, and SCDS-001. Concludes with an executive summary on whether B4 Slice 3 is
architecturally ready to begin. **No code, migration, or API is authorized by this document.**

**Date:** 2026-07-24

**Reviewed:** `docs/adr/ADR-021-spatial-conflict-detection-and-controlled-cross-tenant-intelligence.md`
(Proposed), `docs/SCDS-001-spatial-conflict-detection-specification.md` (Draft), against
`docs/B4_THREAT_MODEL.md`, `docs/adr/ADR-022-spatial-authorization-model.md` (Accepted, frozen),
`docs/adr/ADR-017-b3-platform-freeze.md` (Accepted, frozen), and every other frozen B1–B3 ADR
reachable from those.

---

## Step 1 — Architectural review of ADR-021

Reviewed against each named criterion. **Verdict: no blocking inconsistency found.** One item is
flagged as correctly deferred rather than resolved by ADR-021 itself — noted below, and confirmed
resolved by SCDS-001 §5.

| Criterion | Finding |
|---|---|
| **DDD consistency** | Pass. ADR-021 §5/§6 keep `ParcelGeometry` and `Parcel` exactly as ADR-018/ADR-013 defined them — no field, status, or invariant added to either aggregate. The conflict-detection service is modeled as an application-layer service, not a domain entity, consistent with this codebase's existing ports-and-adapters discipline (ADR-002). |
| **Platform Kernel consistency** | Pass. ADR-021 §7 reuses the kernel `audit()` mechanism (ADR-007) unchanged, and its attribution model ("attributable to the request that triggered it") is consistent with `ExecutionContext.principal_id` — the same mechanism every prior audited action in this codebase uses. No new kernel primitive is proposed. |
| **Registry/Spatial separation** | Pass. ADR-021 §5 is explicit: Registry stays authoritative for identity, Spatial for geometry, conflict detection is Spatial-internal. Registry's own code is confirmed untouched — no new Registry-facing interface is introduced, and the existing `ParcelExistencePort` (Slice 2) is the only cross-context read named, unextended beyond its current shape. |
| **Controlled Platform Authority doctrine** | Pass, with one item correctly deferred (see below). ADR-021 §1 satisfies `docs/ENGINEERING_RULES.md` rule 9's four conditions (fixed at call site, read-only, narrow, audited) at the *policy* level. The exact *mechanism* by which the cross-tenant read is achieved at the RLS layer is not specified in ADR-021 — this is appropriate, since ADR-021 explicitly excludes "algorithm, query design" from its own scope, and the mechanism question is a query-design question. **Resolved by SCDS-001 §5**, which specifies the mechanism's required shape (a fixed, request-scoped, non-caller-influenced elevated context, structurally analogous to the existing `app.is_super_admin` session variable — never a blanket RLS policy relaxation) without committing to its literal implementation. |
| **RLS consistency** | Pass, same finding as above. ADR-021 §8 confirms RLS is not relaxed or given a second unconditional bypass; SCDS-001 §5 confirms the specific mechanism must be scoped to exactly one fixed query and torn down immediately, mirroring `context_hydration`'s own existing precedent. No RLS policy defined by migration `0010` is proposed for modification. |
| **Cross-tenant information leakage** | Pass. ADR-021 §3 (minimal-disclosure default) and §7 (audit payload may hold investigative detail without that detail reaching the API response) are internally consistent — the audit log and the API response are correctly treated as two different surfaces with two different disclosure rules, matching this platform's existing precedent (e.g., Registry's `mutation_denied` audit entries record more than any error response ever discloses). |
| **Audit completeness** | Pass. ADR-021 §7, refined by SCDS-001 §7, covers every state this taxonomy can produce: no-conflict (audited as a completed check, not skipped), a geometric finding, a governance review of that finding, and a governance confirmation — plus a defensive "unauthorized invocation" event SCDS-001 adds for Slice 3's own live-verification use. No transition was found to lack a corresponding audit event. |
| **Principle of Least Privilege** | Pass. ADR-021 §1/§8 and SCDS-001 §5 all converge on the same shape: the cross-tenant read is a fixed, bounded-neighbourhood query, never a general grant, and no second exception may reuse it (ADR-021 §1's "no second exception inherits this one," restated platform-wide in `docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`). |
| **Existing ADR compatibility** | Pass. Checked explicitly against ADR-017 (B3 freeze — Registry's frozen scope is not touched; the only Registry read used, `ParcelExistencePort`, already existed before this review), ADR-018 (unaffected, confirmed in ADR-021's own "Relationship to ADR-018" section), ADR-019 (unaffected, no `GeometryPort` change), ADR-022 (not weakened — ADR-022 §11 explicitly anticipated and reserved this exact relationship, and ADR-021's own text quotes that reservation), ADR-011 (delegation reused unchanged, no new delegation mechanism), ADR-013 (`Parcel.tenant_id`/`created_by` read, never modified), ADR-007 (audit mechanism reused, not duplicated), ADR-009/ADR-012 (B1/B2 frozen scope — Identity's role set and kernel primitives are read, never modified). No contradiction found against any frozen ADR. |
| **Amendment compliance** | Pass. ADR-021 modifies no frozen ADR's text — every relationship is expressed as an extension by reference (`docs/adr/ADR-021-...md`'s own "Relationship to ADR-01x" sections), matching this platform's standing convention that a frozen decision is only ever extended, never silently altered. |

**Overall Step 1 conclusion:** ADR-021, as drafted, requires **no amendment**. The one item this
review would otherwise have required ADR-021 to resolve (the RLS-bypass mechanism's exact shape)
is correctly out of an *architecture* ADR's scope and is fully addressed by SCDS-001 §5 instead —
this is evidence the two-tier ADR/specification structure this governance package introduced is
working as intended, not a gap in either document.

---

## Step 3 — Package-level coherence review

Reviewed `docs/B4_THREAT_MODEL.md`, ADR-021, ADR-022, and SCDS-001 together, as one coherent
package, per the specific checks requested:

- **No contradictions.** TB5's five requirements (information disclosure, elevation of privilege,
  tampering, denial of service, repudiation) are each traced to a specific resolving section:
  disclosure → ADR-021 §3/SCDS-001 §4; elevation of privilege → ADR-021 §1/SCDS-001 §5; tampering →
  named as ADR-020's job, orthogonal, not silently absorbed into this package; denial of service →
  SCDS-001 §6 (specification of expectations, no implementation); repudiation → ADR-021 §7/SCDS-001
  §7. No requirement was found unaddressed or addressed twice in conflicting ways.
- **No duplicated responsibilities.** ADR-022's same-tenant creator-or-governance model and
  ADR-021's cross-tenant conflict-detection model are additive, not overlapping — ADR-022 governs
  who may mutate a `ParcelGeometry`; ADR-021 governs what happens, read-only, alongside an
  already-authorized mutation. Confirmed no code path exists (or is proposed) where the two models
  could produce conflicting authorization decisions for the same operation, since ADR-021's
  cross-tenant read is explicitly not itself a mutation-authorization decision.
- **No authorization debt.** Unlike Slice 1's shipped-then-escalated coarse gate (the
  ADR-005-shaped gap ADR-022 closed), this package resolves its authorization model (who may see
  what, §3/§4, "Cross-Tenant Visibility"/"Disclosure Matrix") *before* any implementation, matching
  the discipline this platform committed to after that historical pattern repeated once already in
  Spatial's own short history.
- **No RLS violations.** Confirmed above (Step 1) and by SCDS-001 §5's explicit "never a blanket
  relaxation of `parcel_geometries`'s existing RLS policy" constraint.
- **No hidden platform bypasses.** Every cross-tenant/cross-context read named anywhere in this
  package (ADR-021 §1, SCDS-001 §5/§8) is traced to the single, named Controlled Platform
  Authority exception — `docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`'s four-part test was applied
  retroactively to every capability SCDS-001 §8 names as a future extension point (Fraud Engine,
  Risk Engine, AI Analysis, etc.), and each is confirmed, in SCDS-001's own text, to require its
  own separate exception and its own ADR — none is granted implicit reach through this package.
- **No uncontrolled cross-tenant reads.** The only cross-tenant read this entire package
  authorizes (in the sense of "describes precisely enough that Slice 3 could implement it") is the
  one in ADR-021 §1/SCDS-001 §5. No other read — governance-tier disclosure (ADR-021 §3), audit
  payload content (ADR-021 §7/SCDS-001 §7), or any future extension (SCDS-001 §8) — introduces a
  second cross-tenant *read* mechanism; each of those instead consumes the *finding* the one
  authorized read already produced, per `docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`'s fourth
  test criterion.

**Step 3 conclusion:** the package is internally coherent. No amendment to ADR-021, ADR-022, or
the Threat Model is required as a result of this review.

---

## Step 7 — Executive summary: is B4 Slice 3 architecturally ready?

**Architecturally ready to be reviewed for acceptance — not yet ready to be implemented.** These
are different questions, and this package answers only the first:

- The **architecture** (ADR-021) and its **specification** (SCDS-001) are both internally
  consistent, consistent with every frozen and accepted ADR they touch, and resolve every binding
  requirement `docs/B4_THREAT_MODEL.md` TB5 named before either document existed.
- Both documents remain in **Proposed/Draft** status. Per the explicit stop condition governing
  this entire package, **no implementation — overlap detection, duplicate detection, fraud
  detection, conflict scoring, AI analysis, spatial search, or risk engine — is authorized until
  ADR-021 (and, by extension, SCDS-001, which has no independent standing without it) is
  reviewed and explicitly accepted.**
- Three items remain genuinely open and are correctly left open rather than force-closed by this
  review: the exact geometric tolerance for "near duplicate" vs. "duplicate" vs. "merely
  overlapping" (ADR-021's own Risks section, SCDS-001 §1), the exact governance-tier disclosure
  depth on a confirmed conflict (ADR-021 §3, flagged as a product/legal question), and the exact
  RLS-bypass mechanism's literal implementation (SCDS-001 §5, specified in shape only). None of
  these block *accepting* ADR-021/SCDS-001 as the governing architecture — they are exactly the
  questions Slice 3's own implementation proposal must answer, under review, before that
  implementation ships, per ADR-021's own Recommendation section.

**Recommendation:** treat this review, ADR-021, and SCDS-001 as ready for the same explicit
acceptance step every prior ADR in this programme has required, before any Slice 3 work begins.
Until that acceptance is given, this remains a documentation-only milestone.
