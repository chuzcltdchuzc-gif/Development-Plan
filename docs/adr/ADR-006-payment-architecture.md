# ADR-006 — Payment Architecture (Paystack + Stripe)

**Status:** Accepted
**Date:** 2026-07-13

## Context

Both audits found serious payment/credit-ledger defects:

- Base44's `lvServiceBilling` function reserved credits atomically, then created a `ServiceRequest` record, then referenced an **undefined variable** while building its audit-log entry — crashing *after* both prior writes had already committed. The client received a 500 error and never learned the reservation succeeded, so it could never call `complete`/`fail` to release it — a permanent, unbounded credit leak on every failed attempt. Separately, `CreditWallet`'s RLS allowed the record owner to edit their own balance directly, and `OrganizationWallet`/`ServiceRequest`/`Invoice` allowed *any* authenticated user to edit *anyone's* wallet, service request, or invoice.
- Emergent's webhook signature verification (Paystack HMAC-SHA-512 via `hmac.compare_digest`, Stripe via the official SDK's `Webhook.construct_event`) was confirmed **correct** — raw request body used for HMAC, constant-time comparison, correct secret. However, an unauthenticated mock-payment webhook (`POST /api/webhook/mock`) was always mounted regardless of configured provider, letting a user create a real checkout to obtain a legitimate `reference`, never pay, then call the mock endpoint directly to receive real credits for free. A standalone (non-replica-set) MongoDB deployment also silently broke transactional atomicity between the wallet balance update and the transaction-log insert, risking double-crediting on webhook retry.

## Decision

1. **Paystack** (Nigeria-first) and **Stripe** (diaspora/international) as the two payment providers, per the Operator's existing choice.
2. **Reuse Emergent's webhook signature-verification code near-verbatim** — it was audited as cryptographically sound and is not being rewritten from scratch.
3. **No mock/test payment endpoint is ever compiled into a non-development build.** Test payment flows exist only behind a build-time flag that cannot be enabled in staging or production images (not merely an environment-variable check at runtime, which is what failed in the Emergent audit).
4. **All balance-affecting operations go through one atomic ledger function**, backed by a real Postgres transaction (ADR-003) — never a check-then-`$inc`-separately pattern. The database enforces a non-negative balance constraint; the application layer cannot bypass it.
5. **Idempotency keys** on every purchase/consume/refund operation, so a webhook retry or duplicate client request cannot double-apply.
6. Invoices auto-generate on service completion — no admin-gated dead end (Base44's `lvInvoiceGenerator` required admin auth to invoke, but nothing auto-triggered it after service completion, leaving `₦25,000` in confirmed-but-unbilled revenue in the audited data).

## Consequences

- Structurally eliminates the "phantom reservation" and "self-service balance edit" bug classes found in Base44, and the "always-on mock webhook" and "standalone-Mongo breaks atomicity" bugs found in Emergent (moot here since we use Postgres, ADR-003).
- Webhook handler code ports with high confidence directly from Emergent, saving implementation time relative to writing this from scratch.
- Requires the ledger function to be the *only* write path to wallet/invoice/service-request tables — enforced by the RLS/authorization policy required on every entity (`docs/ENGINEERING_RULES.md` §1), not by convention alone.
