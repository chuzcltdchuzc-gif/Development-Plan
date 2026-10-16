"""Evidence Actor Attribution API router — `/v1/evidence` (GD-012, as
amended by GD-013).

Authorized scope is exactly two mutating endpoints (GD-012 §4): recording
and correcting attribution. No GET/list/detail endpoint exists here —
`list_attributions_for_evidence` already exists at the service layer, but
exposing it via HTTP is deliberately excluded (GD-012 §6.2) pending its own,
future, separate Governance act resolving ADR-028's third-party
personal-data disclosure question.

Router-level `require_role(*PARCEL_REGISTRANT_ROLES)` is the coarse gate,
exactly mirroring `evidence_router.py`'s own upload endpoint (GD-012 §5);
`EvidenceActorAttributionService._authorize_mutation`/`_can_mutate` remains
the fine-grained, resource-aware decision, reusing the existing
creator-or-governance-role gate unchanged — no new authorization mechanism
is introduced.

## Function-scoped dependency wiring (GD-013 §3)

This module does NOT use `Depends(get_evidence_actor_attribution_service)`
(the shared provider in `evidence/dependencies.py`, at the FastAPI default
"request" scope). That provider's own `Depends(get_db_session)` calls exit
their cleanup — including the request's final `commit()` — only *after*
the HTTP response has already been transmitted (confirmed directly against
this project's installed FastAPI/Starlette versions: the default-scope
dependency cleanup runs inside `fastapi.routing`'s `request_stack`, which
closes after `await response(...)` is already sent). A commit failure at
that point can therefore never reach the caller as anything but a false
"success" response — exactly the defect GD-013 §3 authorizes closing.

The five provider functions below mirror `evidence/dependencies.py`'s
`get_evidence_repository`, `get_evidence_actor_attribution_repository`,
`get_evidence_parcel_existence_port`, `get_principal_tenant_port`, and
`get_evidence_actor_attribution_service` field-for-field, except that every
`Depends(get_db_session)` here specifies `scope="function"` — FastAPI's
*other* dependency scope, whose cleanup (including the same final
`commit()`) runs inside `fastapi.routing`'s `function_stack`, which closes
*before* the response is sent (GD-013 §3, verified directly against a real
PostgreSQL database during that Decision's own drafting). All five below
share that identical scope, so exactly one session instance serves the
whole request — the mutation and its staged audit event remain on the same
session and the same transaction, exactly as GD-009 Batch 1 requires.

GD-013 §3 conditions 3–4 apply: `evidence/dependencies.py` and
`app/kernel/uow.py` are not edited by this module, and these five providers
are not imported by, or wired into, any other router.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.evidence.adapters.postgres_repositories import (
    PostgresEvidenceActorAttributionRepository,
    PostgresEvidenceRepository,
    PostgresParcelExistenceAdapter,
    PostgresPrincipalTenantAdapter,
)
from app.contexts.evidence.api.attribution_dtos import (
    AttributionResponse,
    CorrectAttributionRequest,
    RecordAttributionRequest,
)
from app.contexts.evidence.application.attribution_service import (
    EvidenceActorAttributionService,
)
from app.contexts.evidence.ports import (
    EvidenceActorAttributionRepository,
    EvidenceRepository,
    ParcelExistencePort,
    PrincipalTenantPort,
)
from app.contexts.registry.domain.value_objects import PARCEL_REGISTRANT_ROLES
from app.kernel.authorization.pep import require_role
from app.kernel.context import ExecutionContext
from app.kernel.uow import get_db_session

router = APIRouter(prefix="/v1/evidence", tags=["evidence-attribution"])

# GD-013 §4: the one database constraint this router is authorized to
# translate into HTTP 409 — identified by both its SQLSTATE and its exact
# name, never by parsing an error message (see `_integrity_diagnostics`
# and `_is_supersedes_once_violation` below).
_SUPERSEDES_ONCE_SQLSTATE = "23505"
_SUPERSEDES_ONCE_CONSTRAINT = "uq_evidence_actor_attributions_supersedes_once"


def _get_evidence_repository(
    session: AsyncSession = Depends(get_db_session, scope="function"),
) -> EvidenceRepository:
    return PostgresEvidenceRepository(session)


def _get_evidence_actor_attribution_repository(
    session: AsyncSession = Depends(get_db_session, scope="function"),
) -> EvidenceActorAttributionRepository:
    return PostgresEvidenceActorAttributionRepository(session)


def _get_evidence_parcel_existence_port(
    session: AsyncSession = Depends(get_db_session, scope="function"),
) -> ParcelExistencePort:
    return PostgresParcelExistenceAdapter(session)


def _get_principal_tenant_port(
    session: AsyncSession = Depends(get_db_session, scope="function"),
) -> PrincipalTenantPort:
    return PostgresPrincipalTenantAdapter(session)


def _get_attribution_service(
    attributions: EvidenceActorAttributionRepository = Depends(
        _get_evidence_actor_attribution_repository
    ),
    evidence: EvidenceRepository = Depends(_get_evidence_repository),
    parcel_existence: ParcelExistencePort = Depends(_get_evidence_parcel_existence_port),
    principal_tenant: PrincipalTenantPort = Depends(_get_principal_tenant_port),
    session: AsyncSession = Depends(get_db_session, scope="function"),
) -> EvidenceActorAttributionService:
    return EvidenceActorAttributionService(
        attributions=attributions,
        evidence=evidence,
        parcel_existence=parcel_existence,
        principal_tenant=principal_tenant,
        session=session,
    )


def _integrity_diagnostics(exc: IntegrityError) -> tuple[str | None, str | None]:
    """Extracts (sqlstate, constraint_name) from the underlying driver
    exception, via structured attributes only — never by parsing
    `str(exc)`/`exc.args` (GD-013 §4). `exc.orig` is SQLAlchemy's asyncpg
    DBAPI-adapter error; `.__cause__` is the real `asyncpg.exceptions.*`
    object, which exposes both fields directly (confirmed against this
    project's installed sqlalchemy/asyncpg versions during GD-013's own
    drafting). Returns `(None, None)` if either is unavailable, rather than
    guessing — an unmatched pair never satisfies `_is_supersedes_once_violation`
    below, so the exception correctly falls through to the unhandled path."""
    orig = getattr(exc, "orig", None)
    driver_exc = getattr(orig, "__cause__", None) or orig
    sqlstate = getattr(driver_exc, "sqlstate", None)
    constraint_name = getattr(driver_exc, "constraint_name", None)
    return sqlstate, constraint_name


def _is_supersedes_once_violation(exc: IntegrityError) -> bool:
    """GD-013 §4: both the SQLSTATE (23505, unique_violation) and the exact
    constraint name must match. Neither alone is sufficient — the
    self-supersession CHECK constraint shares IntegrityError's exception
    class and, being class-23 (23514), could otherwise be misclassified by
    an exception-class-only or SQLSTATE-class-only check."""
    sqlstate, constraint_name = _integrity_diagnostics(exc)
    return sqlstate == _SUPERSEDES_ONCE_SQLSTATE and constraint_name == _SUPERSEDES_ONCE_CONSTRAINT


@router.post(
    "/{evidence_id}/attributions",
    status_code=status.HTTP_201_CREATED,
    response_model=AttributionResponse,
    operation_id="recordEvidenceAttribution",
)
async def record_evidence_attribution(
    evidence_id: str,
    body: RecordAttributionRequest,
    ctx: ExecutionContext = Depends(require_role(*PARCEL_REGISTRANT_ROLES)),
    service: EvidenceActorAttributionService = Depends(_get_attribution_service),
) -> dict:
    return await service.record_attribution(
        ctx=ctx,
        evidence_id=evidence_id,
        attribution_role=body.attribution_role.value,
        actor_reference_kind=body.actor_reference_kind.value,
        actor_type=body.actor_type.value,
        basis=body.basis,
        actor_principal_id=body.actor_principal_id,
        actor_name=body.actor_name,
        actor_organization_name=body.actor_organization_name,
        review_method=body.review_method,
    )


@router.post(
    "/attributions/{attribution_id}/corrections",
    status_code=status.HTTP_201_CREATED,
    response_model=AttributionResponse,
    operation_id="correctEvidenceAttribution",
)
async def correct_evidence_attribution(
    attribution_id: str,
    body: CorrectAttributionRequest,
    ctx: ExecutionContext = Depends(require_role(*PARCEL_REGISTRANT_ROLES)),
    service: EvidenceActorAttributionService = Depends(_get_attribution_service),
) -> dict:
    try:
        return await service.correct_attribution(
            ctx=ctx,
            attribution_id=attribution_id,
            attribution_role=body.attribution_role.value,
            actor_reference_kind=body.actor_reference_kind.value,
            actor_type=body.actor_type.value,
            basis=body.basis,
            actor_principal_id=body.actor_principal_id,
            actor_name=body.actor_name,
            actor_organization_name=body.actor_organization_name,
            review_method=body.review_method,
        )
    except IntegrityError as exc:
        # GD-013 §4: translate ONLY the specifically named, dual-diagnostic
        # -confirmed constraint violation. Any other IntegrityError
        # (including the self-supersession CHECK, which the domain layer
        # treats as structurally unreachable but must not be silently
        # misclassified if it is ever reached) propagates unhandled, as a
        # 5xx — this is a deliberately narrow except clause, not a general
        # database-exception handler.
        if not _is_supersedes_once_violation(exc):
            raise
        # Required, established empirically against real PostgreSQL: once
        # session.flush() raises inside the ORM Session (not merely at the
        # driver/Core level), SQLAlchemy marks that Session's transaction
        # "must rollback" — any further use, including get_db_session's own
        # subsequent `except HTTPException: await session.commit()` branch,
        # raises PendingRollbackError instead of completing. `service.session`
        # is the same function-scoped session all five providers share
        # (GD-013 §3 — one session for the whole request); explicitly
        # rolling it back here, entirely within this router module, is what
        # lets get_db_session's own commit call succeed afterward rather
        # than itself failing and turning this into an unhandled 500.
        await service.session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="attribution has already been superseded by another correction",
        ) from exc
