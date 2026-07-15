"""Append-only, hash-chained audit log (ADR-007).

No update or delete path exists through this module — storage only grows.
Each entry's hash covers its own content plus the previous entry's hash, so
`verify_chain()` can detect tampering by recomputing every hash rather than
trusting a status flag (the exact "security theater" pattern the Emergent
audit found — see docs/adr/ADR-007).
"""
from __future__ import annotations

import hashlib
import json
import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from app.kernel.context import current_context

GENESIS_HASH = "0" * 64


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _compute_hash(
    *,
    entry_id: str,
    action: str,
    resource_type: str,
    resource_id: str | None,
    decision: str | None,
    principal_id: str,
    payload: dict,
    created_at: str,
    prev_hash: str,
) -> str:
    canonical = json.dumps(
        {
            "entry_id": entry_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "decision": decision,
            "principal_id": principal_id,
            "payload": payload,
            "created_at": created_at,
            "prev_hash": prev_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuditEntry:
    entry_id: str
    action: str
    resource_type: str
    resource_id: str | None
    decision: str | None
    principal_id: str
    payload: dict
    created_at: str
    prev_hash: str
    hash: str = field(compare=False)

    def recompute_hash(self) -> str:
        return _compute_hash(
            entry_id=self.entry_id,
            action=self.action,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            decision=self.decision,
            principal_id=self.principal_id,
            payload=self.payload,
            created_at=self.created_at,
            prev_hash=self.prev_hash,
        )


class AuditStore(Protocol):
    async def append(self, entry: AuditEntry) -> None: ...
    async def last_hash(self) -> str: ...
    async def all_entries(self) -> list[AuditEntry]: ...


_store_var: ContextVar[AuditStore | None] = ContextVar("landvault_audit_store", default=None)

# Write-once at startup, read-only afterward — safe as a plain global
# (unlike _store_var, nothing ever mutates this per-request). Backstops
# audit() calls that happen before any per-request session exists, e.g. the
# PEP's authz-deny audit (app.kernel.authorization.pep) runs during
# dependency resolution, before app.kernel.uow.get_db_session is ever
# reached — confirmed against a live server: without this, such a call
# raised "audit store not configured" (RuntimeError -> 500) instead of the
# expected 403.
_eager_fallback: AuditStore | None = None


def configure_eager_fallback(store: AuditStore) -> None:
    global _eager_fallback
    _eager_fallback = store


def configure_audit_store(store: AuditStore) -> Token[AuditStore | None]:
    """A ContextVar, not a plain global: under real concurrent requests
    (each its own asyncio Task), a global would let one request's audit
    store binding stomp another's mid-flight. Production binds this per
    request (app.kernel.uow.get_db_session); tests bind it once per test."""
    return _store_var.set(store)


def reset_audit_store(token: Token[AuditStore | None]) -> None:
    _store_var.reset(token)


def get_audit_store() -> AuditStore:
    store = _store_var.get()
    if store is not None:
        return store
    if _eager_fallback is not None:
        return _eager_fallback
    raise RuntimeError("audit store not configured — call configure_audit_store() at startup")


async def audit(
    action: str,
    *,
    resource_type: str = "unknown",
    resource_id: str | None = None,
    decision: str | None = None,
    payload: dict | None = None,
) -> AuditEntry:
    store = get_audit_store()
    ctx = current_context()
    prev_hash = await store.last_hash()
    entry_id = uuid.uuid4().hex
    created_at = _now_iso()
    payload = payload or {}
    entry_hash = _compute_hash(
        entry_id=entry_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        decision=decision,
        principal_id=ctx.principal_id,
        payload=payload,
        created_at=created_at,
        prev_hash=prev_hash,
    )
    entry = AuditEntry(
        entry_id=entry_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        decision=decision,
        principal_id=ctx.principal_id,
        payload=payload,
        created_at=created_at,
        prev_hash=prev_hash,
        hash=entry_hash,
    )
    await store.append(entry)
    return entry


async def verify_chain() -> bool:
    """Recompute every entry's hash and confirm the chain is unbroken."""
    store = get_audit_store()
    prev = GENESIS_HASH
    for entry in await store.all_entries():
        if entry.prev_hash != prev or entry.recompute_hash() != entry.hash:
            return False
        prev = entry.hash
    return True
