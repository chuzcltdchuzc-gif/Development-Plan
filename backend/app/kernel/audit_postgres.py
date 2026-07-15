"""Postgres-backed implementation of app.kernel.audit.AuditStore.

Lives in the kernel alongside audit_orm.py — audit logging is cross-cutting,
not owned by any single bounded context. tests/fakes/audit_store.py
implements the same protocol for the fast, hermetic acceptance-test suite.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.kernel.audit import GENESIS_HASH, AuditEntry
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

    async def append(self, entry: AuditEntry) -> None:
        self._session.add(
            AuditLogRecord(
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
        )
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
