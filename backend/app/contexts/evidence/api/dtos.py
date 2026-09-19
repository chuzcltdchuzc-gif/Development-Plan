"""Evidence API response shapes (B5 IMVP-5). Mirrors
`evidence_service._evidence_view` field-for-field for the subset actually
useful to a client at this phase (OpenAPI Source-of-Truth Hardening
convention, PR #18) — `storage_key` (storage-internal) and `audit_ref`
(audit-internal) are deliberately omitted, not secrets, just not
information a caller needs. `tenant_id`/`worm_grade`/`legal_hold*` are
also omitted: tenant is implicit in the authenticated session, and
worm_grade/legal_hold are always empty at this phase (IMVP-5 never seals,
never applies a hold) — omitting rather than always-null keeps the
contract honest about what this phase actually does, per LV-000's
non-adjudication and "no invented confidence" doctrine.

There is no request DTO here: the upload endpoint takes its file as a raw
request body (see api/evidence_router.py's own comment on why — Engineering
Rule 5 preflight, no `python-multipart` in this project's dependency set)
and its metadata as query parameters, validated inline by FastAPI's own
Enum/str parameter typing — nothing here needs a Pydantic request model.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, WithJsonSchema

from app.contexts.evidence.domain.evidence_record import EVIDENCE_TYPES


class EvidenceType(StrEnum):
    """Mirrors `app.contexts.evidence.domain.evidence_record.EVIDENCE_TYPES`
    exactly (ADR-026) — kept in sync by the assertion in
    tests/test_evidence_api.py, not by import, since the domain layer uses
    a plain frozenset (no framework coupling), not an enum."""

    SURVEY_PLAN = "SURVEY_PLAN"
    TITLE_DOCUMENT = "TITLE_DOCUMENT"
    IDENTITY_DOCUMENT = "IDENTITY_DOCUMENT"
    OTHER = "OTHER"


assert {t.value for t in EvidenceType} == EVIDENCE_TYPES, "EvidenceType drifted from the domain"


class EvidenceStatus(StrEnum):
    """Mirrors `evidence_record.STATUS_*` — IMVP-5 only ever produces
    RECEIVED/HASHED; SEALED exists on the domain model but no code path
    in this slice ever reaches it (seal() is not called anywhere in the
    upload path, and no endpoint exposes it)."""

    RECEIVED = "RECEIVED"
    HASHED = "HASHED"
    SEALED = "SEALED"


class EvidenceResponse(BaseModel):
    """Response shape for both Evidence endpoints. Mirrors
    `evidence_service._evidence_view`'s field-for-field truth for the
    fields a client needs — see module docstring for what's omitted and
    why."""

    evidence_id: str
    parcel_id: str
    uploaded_by: str
    filename: str
    mime_type: str
    # OpenAPI `type: number`, not `integer` — same orval/zod-v3 generator-
    # compatibility workaround as GeometryResponse.srid/TokenResponse.
    # expires_in (see those comments); wire value is still a plain int.
    size_bytes: Annotated[int, WithJsonSchema({"type": "number", "title": "Size Bytes"})]
    basis: str
    evidence_type: EvidenceType
    status: EvidenceStatus
    sha256: str | None = None
    created_at: str
