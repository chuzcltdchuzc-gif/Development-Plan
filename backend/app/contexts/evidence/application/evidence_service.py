"""EvidenceService — Evidence context's use-cases (B5 Slice B5.2, docs/adr/
ADR-026-evidence-domain-model.md).

Scope discipline, stated plainly per the Governance Authority's B5.2
authorization: this service does NOT compute hashes and does NOT call
StoragePort. `record_upload` accepts an already-written `storage_key` as a
parameter (as if a caller — B5.3's upload endpoint, not built yet — already
called StoragePort.put()); `mark_hashed`/`seal` accept an already-computed
`sha256`/already-reported `worm_grade` the same way. This mirrors exactly
how ParcelService.create_parcel does not compute `parcel_number` itself —
that is ParcelNumberAllocator's job, injected as a separate port
(docs/adr/ADR-014) — orchestration and computation are kept as distinct
responsibilities here for the identical reason.

No upload endpoint exists yet, so no router calls this service in this
slice — it exists to prove the repository/domain/DI wiring end-to-end
(the Governance Authority's explicit B5.2 scope) and to give B5.3 a real
seam to call into rather than a retrofit.

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

import uuid

from fastapi import HTTPException, status

from app.contexts.evidence.domain.evidence_record import (
    EvidenceLifecycleError,
    EvidenceRecord,
    EvidenceSealedError,
)
from app.contexts.evidence.ports import EvidenceRepository
from app.kernel.audit import audit
from app.kernel.context import ExecutionContext


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
    def __init__(self, *, evidence: EvidenceRepository) -> None:
        self.evidence = evidence

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
