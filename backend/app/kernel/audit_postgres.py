"""Postgres-backed implementation of app.kernel.audit.AuditStore.

Lives in the kernel alongside audit_orm.py — audit logging is cross-cutting,
not owned by any single bounded context. tests/fakes/audit_store.py
implements the same protocol for the fast, hermetic acceptance-test suite.

Also home to `audit_staged()` (GD-009 Batch 1, docs/adr/ADR-029,
docs/GD-009-audit-transaction-semantics-implementation-authorization-and-
adr-007-regularisation.md, resumed under docs/GD-011-gd009-batch1-
resumption-authorization.md) — the explicit, transaction-coupled
successful-mutation audit path. It lives here, not in app.kernel.audit,
because it is inherently Postgres/session-specific (it takes the caller's
own AsyncSession directly), unlike audit()'s storage-agnostic AuditStore
Protocol resolution.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.kernel.audit import GENESIS_HASH, AuditEntry, _build_entry
from app.kernel.audit_orm import AuditLogRecord


def _looks_like_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


class PostgresAuditStore:
    """UPDATE/DELETE on this table are revoked at the database-grant level
    for the application role (migrations/versions/0002) — this class
    simply never attempts them."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_record(self, entry: AuditEntry) -> AuditLogRecord:
        return AuditLogRecord(
            id=uuid.UUID(entry.entry_id) if _looks_like_uuid(entry.entry_id) else uuid.uuid4(),
            action=entry.action,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            decision=entry.decision,
            principal_id=entry.principal_id,
            payload=entry.payload,
            prev_hash=entry.prev_hash,
            hash=entry.hash,
            # MUST match entry.created_at exactly — it's part of the
            # hashed content (app.kernel.audit._compute_hash). Letting
            # the column's server_default=func.now() generate its own
            # value here means the persisted created_at never matches
            # what was actually hashed, so verify_chain() fails on every
            # single entry — confirmed against a live Postgres.
            created_at=datetime.fromisoformat(entry.created_at),
        )

    async def append(self, entry: AuditEntry) -> None:
        self._session.add(self._to_record(entry))
        # Commits immediately — NOT just flush(). An audit entry must be
        # durable the instant it's recorded, independent of whatever the
        # rest of the request does afterward. Confirmed against a live
        # server: app.kernel.uow.get_db_session rolls back the whole
        # transaction when a route handler raises (its normal behavior for
        # an expected 401/403), which silently discarded exactly the
        # deny/failure audit entries — e.g. "identity.refresh.
        # replay_detected" — that a real audit trail most needs to keep.
        # SQLAlchemy auto-begins a fresh transaction after this commit, so
        # whatever the caller does next in the same session is unaffected.
        await self._session.commit()

    async def append_staged(self, entry: AuditEntry) -> None:
        """GD-009 Batch 1 — stages the row into this session via `add()` +
        `flush()` only. Deliberately never commits: the caller's own
        transaction (app.kernel.uow.get_db_session's single, final
        `await session.commit()`) remains the sole commit point, so this
        row becomes durable, or is rolled back, together with whatever
        else that transaction does — the same non-intermediate-commit
        discipline GD-009 §10 requires to avoid silently clearing the
        request's RLS `is_local` scoping. Not part of the `AuditStore`
        Protocol (app.kernel.audit.AuditStore) and never called by
        `audit()` or by `get_audit_store()`'s resolution — only by
        `audit_staged()` below, invoked explicitly, by name, at an
        authorized call site."""
        self._session.add(self._to_record(entry))
        await self._session.flush()

    async def last_hash(self) -> str:
        result = await self._session.execute(
            select(AuditLogRecord.hash).order_by(AuditLogRecord.created_at.desc()).limit(1)
        )
        row = result.scalar_one_or_none()
        return row or GENESIS_HASH

    async def all_entries(self) -> list[AuditEntry]:
        result = await self._session.execute(
            select(AuditLogRecord).order_by(AuditLogRecord.created_at.asc())
        )
        return [
            AuditEntry(
                # .hex, NOT str(): entry_id was originally uuid.uuid4().hex
                # (32 chars, no hyphens) and is part of the hashed content —
                # str(uuid.UUID(...)) produces the canonical 36-char
                # hyphenated form, a different string for the same UUID
                # value, which silently broke every hash's recomputation
                # (confirmed against a live Postgres: prev_hash linkage was
                # intact but recompute_hash() never matched the stored hash).
                entry_id=record.id.hex,
                action=record.action,
                resource_type=record.resource_type,
                resource_id=record.resource_id,
                decision=record.decision,
                principal_id=record.principal_id,
                payload=record.payload,
                created_at=record.created_at.isoformat(),
                prev_hash=record.prev_hash,
                hash=record.hash,
            )
            for record in result.scalars()
        ]


class EagerPostgresAuditStore:
    """Fallback store for `audit()` calls that happen before any per-request
    Unit-of-Work session exists — e.g. the PEP's authz-deny audit call
    (app.kernel.authorization.pep), which runs during dependency resolution,
    before app.kernel.uow.get_db_session is ever reached. Confirmed against
    a live server: without this, such calls raised "audit store not
    configured" (RuntimeError -> 500) instead of the expected 403.

    Wraps a session_factory, not a single session — opens, uses, and
    commits/closes a fresh session per method call. Slightly less efficient
    than the per-request PostgresAuditStore, but safe under real concurrency
    (no session shared across requests); only used for audit calls outside
    the normal per-request path, which are comparatively rare.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def append(self, entry: AuditEntry) -> None:
        async with self._session_factory() as session:
            # PostgresAuditStore.append() commits internally.
            await PostgresAuditStore(session).append(entry)

    async def last_hash(self) -> str:
        async with self._session_factory() as session:
            return await PostgresAuditStore(session).last_hash()

    async def all_entries(self) -> list[AuditEntry]:
        async with self._session_factory() as session:
            return await PostgresAuditStore(session).all_entries()


async def audit_staged(
    session: AsyncSession,
    action: str,
    *,
    resource_type: str = "unknown",
    resource_id: str | None = None,
    decision: str | None = None,
    payload: dict | None = None,
    entry_id: str | None = None,
) -> AuditEntry:
    """GD-009 Batch 1 (docs/adr/ADR-029, docs/GD-009-...,
    docs/GD-011-gd009-batch1-resumption-authorization.md) — explicit,
    transaction-coupled successful-mutation audit staging.

    Stages the audit row into the CALLER'S OWN, already-open `session` via
    `PostgresAuditStore.append_staged()` (`add()` + `flush()`, never
    `commit()`), so it becomes durable, or is rolled back, together with
    whatever mutation the caller is already committing in that same
    session — exactly at that session's own single, final commit point
    (app.kernel.uow.get_db_session). No intermediate commit is introduced
    anywhere in this function.

    Must be called explicitly, by name, at an authorized call site only
    (GD-009 Batch 1: app.contexts.evidence.application.attribution_service.
    EvidenceActorAttributionService.record_attribution/correct_attribution).
    This function is completely independent of app.kernel.audit.audit(),
    get_audit_store(), configure_audit_store(), and _store_var: calling it
    does not read, set, or reset any of those, and has zero effect on any
    other audit() call in this or any other request. It is not reachable
    through any ambient, global, request-scoped, session-scoped, ContextVar,
    or dependency-container mechanism — only by importing and calling this
    function directly, at the sites GD-009 authorizes.

    Never use this for denial or failure audits — they must keep calling
    audit() unchanged, per GD-009 §9 and ADR-029 §6 (their entire value is
    surviving a rollback this function's own staged row is specifically
    designed *not* to survive)."""
    store = PostgresAuditStore(session)
    entry = await _build_entry(
        store,
        action,
        resource_type=resource_type,
        resource_id=resource_id,
        decision=decision,
        payload=payload,
        entry_id=entry_id,
    )
    await store.append_staged(entry)
    return entry
