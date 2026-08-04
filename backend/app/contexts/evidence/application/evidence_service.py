"""EvidenceService — Evidence context's use-cases (B5 Slices B5.2/B5.3,
docs/adr/ADR-026-evidence-domain-model.md).

`record_upload` (B5.2) accepts an already-written `storage_key` as a
parameter — a lower-level primitive for "record metadata for content that
was already placed in storage by some other, earlier means." `upload_evidence`
(B5.3) is the real, end-to-end orchestration: it computes the SHA-256 itself
from the bytes it receives, calls StoragePort, persists, and performs the
independent read-back re-hash ADR-007 decision 4 requires — no client-supplied
hash claim is ever trusted, and no hash is ever recorded without having been
confirmed against what storage actually holds.

No upload HTTP endpoint exists yet in this slice — no router calls
`upload_evidence` yet. It exists as the real orchestration seam a future
endpoint calls into.

Role-gating (which roles may upload/hash/seal/hold evidence) is
deliberately not decided here — docs/adr/ADR-026-evidence-domain-model.md
"Out of scope" explicitly defers "exact API URL shape and role-gating" to a
later decision, mirroring how docs/adr/
ADR-013-parcel-aggregate-registry-domain-model.md decided Parcel's domain
model without deciding mutation authorization (that came later, as ADR-015).
What IS enforced here, consistent with every other context in this
codebase: tenant scope, at the same second, independent application layer
every tenant-scoped read/write in this platform uses alongside RLS
(LV-000 v1.8 Article XI §1).
"""
from __future__ import annotations

import hashlib
import uuid

from fastapi import HTTPException, status

from app.contexts.evidence.domain.evidence_record import (
    EvidenceLifecycleError,
    EvidenceRecord,
    EvidenceSealedError,
)
from app.contexts.evidence.ports import EvidenceRepository, StoragePort
from app.kernel.audit import audit
from app.kernel.context import ExecutionContext


class EvidenceIntegrityError(Exception):
    """Raised when the independent read-back re-hash (ADR-007 decision 4)
    does not match the hash computed from the bytes this request received.
    Always a genuine defect (a storage adapter that silently corrupted or
    substituted data) or an active tampering attempt — never a normal,
    expected outcome. Callers must not swallow this; the corresponding
    EvidenceRecord is left at RECEIVED, never marked HASHED, so no reader
    of the record can mistake it for one whose integrity was confirmed."""


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="evidence record not found")


def _in_scope(ctx: ExecutionContext, resource_tenant_id: str) -> bool:
    """Mirrors app.contexts.registry.application.parcel_service._in_scope
    exactly — duplicated locally rather than imported, per the same
    reasoning docs/adr/ADR-013's "known, small, deliberate duplication"
    section already gave: a third occurrence is the trigger to promote this
    into the kernel, not presupposed here."""
    return resource_tenant_id == ctx.tenant_id or ctx.has_any_role("super_admin")


def _evidence_view(record: EvidenceRecord) -> dict:
    return {
        "evidence_id": record.evidence_id,
        "tenant_id": record.tenant_id,
        "parcel_id": record.parcel_id,
        "uploaded_by": record.uploaded_by,
        "filename": record.filename,
        "mime_type": record.mime_type,
        "size_bytes": record.size_bytes,
        "storage_key": record.storage_key,
        "basis": record.basis,
        "evidence_type": record.evidence_type,
        "status": record.status,
        "sha256": record.sha256,
        "worm_grade": record.worm_grade,
        "legal_hold": record.legal_hold,
        "legal_hold_reason": record.legal_hold_reason,
        "legal_hold_by": record.legal_hold_by,
        "audit_ref": record.audit_ref,
        "created_at": record.created_at,
    }


class EvidenceService:
    def __init__(self, *, evidence: EvidenceRepository, storage: StoragePort) -> None:
        self.evidence = evidence
        self.storage = storage

    async def upload_evidence(
        self,
        *,
        ctx: ExecutionContext,
        parcel_id: str,
        filename: str,
        mime_type: str,
        data: bytes,
        basis: str,
        evidence_type: str,
    ) -> dict:
        """The real B5.3 upload path: hash -> store -> persist (RECEIVED) ->
        audit -> independent read-back re-hash -> mark_hashed -> persist ->
        audit, in exactly that order (docs/adr/ADR-026-evidence-domain-model.md
        "Transaction boundaries"). `data` is the complete request body,
        already resolved to bytes by the caller — true chunked/streamed
        hashing of a live HTTP multipart body is deferred to whichever slice
        adds the actual upload endpoint; this method's own hashing is
        already correct and reusable once that endpoint exists, only its
        input-acquisition step would change."""
        if not ctx.tenant_id:
            raise _bad_request("caller has no tenant to record evidence within")
        if not data:
            raise _bad_request("uploaded content is empty")

        # Server-side hash of the bytes this request actually received —
        # never a client-supplied hash claim (ADR-007 decision 4).
        upload_sha256 = hashlib.sha256(data).hexdigest()
        size_bytes = len(data)

        # StoragePort.put takes an opaque, caller-chosen key — it does not
        # generate or return one (app.contexts.evidence.ports.StoragePort).
        storage_key = f"evidence/{ctx.tenant_id}/{parcel_id}/{uuid.uuid4().hex}"

        # The storage write must complete BEFORE the EvidenceRecord row is
        # persisted (ADR-026 "Transaction boundaries") — if this raises, no
        # row is ever created, so there is nothing to roll back at the
        # database layer; the failure propagates to the caller unchanged.
        await self.storage.put(storage_key, data, content_type=mime_type)

        audit_id = uuid.uuid4().hex
        try:
            record = EvidenceRecord.new(
                tenant_id=ctx.tenant_id,
                parcel_id=parcel_id,
                uploaded_by=ctx.principal_id,
                filename=filename,
                mime_type=mime_type,
                size_bytes=size_bytes,
                storage_key=storage_key,
                basis=basis,
                evidence_type=evidence_type,
                audit_ref=audit_id,
            )
        except ValueError as exc:
            raise _bad_request(str(exc)) from exc

        record = await self.evidence.add(record)
        await audit(
            "evidence.uploaded",
            entry_id=audit_id,
            resource_type="evidence_record",
            resource_id=record.evidence_id,
            decision="PERMIT",
            payload={
                "tenant_id": record.tenant_id,
                "parcel_id": record.parcel_id,
                "evidence_type": record.evidence_type,
                "size_bytes": record.size_bytes,
            },
        )

        # Independent read-back re-hash (ADR-007 decision 4) — re-reads what
        # storage actually holds; upload_sha256 above is never trusted on
        # its own as the recorded, authoritative hash.
        readback = await self.storage.get(storage_key)
        readback_sha256 = hashlib.sha256(readback).hexdigest()
        if readback_sha256 != upload_sha256:
            await audit(
                "evidence.integrity_check_failed",
                resource_type="evidence_record",
                resource_id=record.evidence_id,
                decision="DENY",
                payload={
                    "tenant_id": record.tenant_id,
                    "upload_sha256": upload_sha256,
                    "readback_sha256": readback_sha256,
                },
            )
            raise EvidenceIntegrityError(
                f"read-back hash does not match upload-time hash for evidence "
                f"{record.evidence_id}"
            )

        record.mark_hashed(sha256=readback_sha256)
        record = await self.evidence.mark_hashed(record)
        await audit(
            "evidence.hashed",
            resource_type="evidence_record",
            resource_id=record.evidence_id,
            decision="PERMIT",
            payload={"tenant_id": record.tenant_id, "sha256": record.sha256},
        )
        return _evidence_view(record)

    async def record_upload(
        self,
        *,
        ctx: ExecutionContext,
        parcel_id: str,
        filename: str,
        mime_type: str,
        size_bytes: int,
        storage_key: str,
        basis: str,
        evidence_type: str,
    ) -> dict:
        if not ctx.tenant_id:
            raise _bad_request("caller has no tenant to record evidence within")

        # Pre-generated, exactly as app.contexts.registry.application.
        # parcel_service.create_parcel does for its history rows: the
        # record's own audit_ref must be set BEFORE it is persisted, so the
        # row that resolves it is durable no matter which of the two
        # (the row, or the audit store's own independent eager commit,
        # app.kernel.audit_postgres.PostgresAuditStore.append()) becomes
        # durable first.
        audit_id = uuid.uuid4().hex
        try:
            record = EvidenceRecord.new(
                tenant_id=ctx.tenant_id,
                parcel_id=parcel_id,
                uploaded_by=ctx.principal_id,
                filename=filename,
                mime_type=mime_type,
                size_bytes=size_bytes,
                storage_key=storage_key,
                basis=basis,
                evidence_type=evidence_type,
                audit_ref=audit_id,
            )
        except ValueError as exc:
            raise _bad_request(str(exc)) from exc

        record = await self.evidence.add(record)

        await audit(
            "evidence.uploaded",
            entry_id=audit_id,
            resource_type="evidence_record",
            resource_id=record.evidence_id,
            decision="PERMIT",
            payload={
                "tenant_id": record.tenant_id,
                "parcel_id": record.parcel_id,
                "evidence_type": record.evidence_type,
            },
        )
        return _evidence_view(record)

    async def get_evidence(self, *, ctx: ExecutionContext, evidence_id: str) -> dict:
        record = await self.evidence.get(evidence_id)
        if not record or not _in_scope(ctx, record.tenant_id):
            raise _not_found()
        return _evidence_view(record)

    async def list_evidence_for_parcel(
        self, *, ctx: ExecutionContext, parcel_id: str
    ) -> list[dict]:
        records = await self.evidence.list_for_parcel(parcel_id)
        return [_evidence_view(r) for r in records if _in_scope(ctx, r.tenant_id)]

    async def _load_in_scope(self, *, ctx: ExecutionContext, evidence_id: str) -> EvidenceRecord:
        record = await self.evidence.get(evidence_id)
        if not record or not _in_scope(ctx, record.tenant_id):
            raise _not_found()
        return record

    async def mark_hashed(self, *, ctx: ExecutionContext, evidence_id: str, sha256: str) -> dict:
        record = await self._load_in_scope(ctx=ctx, evidence_id=evidence_id)
        try:
            record.mark_hashed(sha256=sha256)
        except EvidenceSealedError as exc:
            raise _conflict(str(exc)) from exc
        except EvidenceLifecycleError as exc:
            raise _conflict(str(exc)) from exc
        except ValueError as exc:
            raise _bad_request(str(exc)) from exc

        record = await self.evidence.mark_hashed(record)
        await audit(
            "evidence.hashed",
            resource_type="evidence_record",
            resource_id=record.evidence_id,
            decision="PERMIT",
            payload={"tenant_id": record.tenant_id, "sha256": record.sha256},
        )
        return _evidence_view(record)

    async def seal(self, *, ctx: ExecutionContext, evidence_id: str, worm_grade: str) -> dict:
        record = await self._load_in_scope(ctx=ctx, evidence_id=evidence_id)
        try:
            record.seal(worm_grade=worm_grade)
        except EvidenceSealedError as exc:
            raise _conflict(str(exc)) from exc
        except EvidenceLifecycleError as exc:
            raise _conflict(str(exc)) from exc
        except ValueError as exc:
            raise _bad_request(str(exc)) from exc

        record = await self.evidence.seal(record)
        await audit(
            "evidence.sealed",
            resource_type="evidence_record",
            resource_id=record.evidence_id,
            decision="PERMIT",
            payload={"tenant_id": record.tenant_id, "worm_grade": record.worm_grade},
        )
        return _evidence_view(record)

    async def apply_legal_hold(
        self, *, ctx: ExecutionContext, evidence_id: str, reason: str
    ) -> dict:
        record = await self._load_in_scope(ctx=ctx, evidence_id=evidence_id)
        try:
            record.apply_legal_hold(reason=reason, applied_by=ctx.principal_id)
        except ValueError as exc:
            raise _bad_request(str(exc)) from exc

        record = await self.evidence.set_legal_hold(record)
        await audit(
            "evidence.legal_hold.applied",
            resource_type="evidence_record",
            resource_id=record.evidence_id,
            decision="PERMIT",
            payload={"tenant_id": record.tenant_id, "reason": reason},
        )
        return _evidence_view(record)

    async def release_legal_hold(self, *, ctx: ExecutionContext, evidence_id: str) -> dict:
        record = await self._load_in_scope(ctx=ctx, evidence_id=evidence_id)
        record.release_legal_hold()

        record = await self.evidence.set_legal_hold(record)
        await audit(
            "evidence.legal_hold.released",
            resource_type="evidence_record",
            resource_id=record.evidence_id,
            decision="PERMIT",
            payload={"tenant_id": record.tenant_id},
        )
        return _evidence_view(record)
