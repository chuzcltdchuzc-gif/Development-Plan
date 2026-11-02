"""Evidence API router — /v1/parcels/{parcel_id}/evidence (B5 IMVP-5, the
first real Evidence HTTP surface; B5.0-B5.3 built the domain/application
foundation this router finally connects to a caller).

Upload is a raw-bytes request body, not `multipart/form-data` — a
deliberate Engineering Rule 5 preflight finding, not a shortcut: this
project's pyproject.toml does not declare `python-multipart` (only pulled
in by FastAPI's `[standard]`/`[all]` extras, neither of which this
project uses), and FastAPI's `UploadFile`/`File()` raise at request time
without it. A raw body plus query-parameter metadata needs no multipart
parsing at all and is not an unusual shape for a single-file upload
endpoint (the same style S3's/Azure Blob's own PUT-object APIs use) — so
no new dependency was introduced rather than working around the gap with
something awkward.

Router-level `require_role(*PARCEL_REGISTRANT_ROLES)` on upload is the
coarse gate (holding a registrant role is necessary to reach this
endpoint at all); `EvidenceService.upload_evidence`'s own creator-or-
governance check (mirroring parcel_router.py's identical two-tier split)
is the fine-grained, resource-aware one that actually decides per parcel.
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status

from app.contexts.evidence.api.dtos import EvidenceResponse, EvidenceType
from app.contexts.evidence.application.evidence_service import EvidenceService
from app.contexts.evidence.dependencies import get_evidence_service
from app.contexts.registry.domain.value_objects import PARCEL_REGISTRANT_ROLES
from app.kernel.authorization.pep import require_auth, require_role
from app.kernel.context import ExecutionContext

# Conservative pilot defaults (docs/ENGINEERING_RULES.md rule 4 — a
# reasonable default rather than unrestricted uploads where no governed
# policy exists yet). Configurable implementation constants, not a
# constitutional/product invariant — a future slice may relax or move
# these to Settings without an architecture decision.
ALLOWED_MIME_TYPES: frozenset[str] = frozenset({"application/pdf", "image/jpeg", "image/png"})
MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MiB

router = APIRouter(prefix="/v1/parcels/{parcel_id}/evidence", tags=["evidence"])


@router.post(
    "",
    status_code=201,
    response_model=EvidenceResponse,
    operation_id="uploadParcelEvidence",
)
async def upload_parcel_evidence(
    parcel_id: str,
    request: Request,
    data: bytes = Body(..., media_type="application/octet-stream"),
    filename: str = Query(..., min_length=1, max_length=255),
    evidence_type: EvidenceType = Query(...),
    basis: str = Query(..., min_length=1, max_length=500),
    ctx: ExecutionContext = Depends(require_role(*PARCEL_REGISTRANT_ROLES)),
    evidence_service: EvidenceService = Depends(get_evidence_service),
) -> dict:
    # Server-derived from the request's own Content-Type header — never a
    # client-supplied "trust me" field, and never the raw client-declared
    # Content-Length either: size below is measured from the bytes
    # actually received (FastAPI's own `data: bytes` body parameter), not
    # any header claim.
    content_type = (request.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported content type: {content_type or '(missing)'}",
        )

    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="uploaded content is empty")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"file exceeds the {MAX_UPLOAD_BYTES}-byte limit",
        )

    return await evidence_service.upload_evidence(
        ctx=ctx,
        parcel_id=parcel_id,
        filename=filename,
        mime_type=content_type,
        data=data,
        basis=basis,
        evidence_type=evidence_type.value,
    )


@router.get("", response_model=list[EvidenceResponse], operation_id="listParcelEvidence")
async def list_parcel_evidence(
    parcel_id: str,
    ctx: ExecutionContext = Depends(require_auth),
    evidence_service: EvidenceService = Depends(get_evidence_service),
) -> list[dict]:
    return await evidence_service.list_evidence_for_parcel(ctx=ctx, parcel_id=parcel_id)
