"""Placeholder GeometryPort adapter (B3 slice 4, docs/adr/ADR-016; signature
amended B4, docs/adr/ADR-019).

Deliberately not a feature: `reference_is_valid` always returns `True`,
validating nothing about the reference's content or about whether it
actually belongs to `tenant_id`/`parcel_id`. This exists so Registry can
be wired, tested, and deployed today with a functioning
dependency-injection seam ("ports before adapters") without depending on
any GIS infrastructure. A future Spatial Intelligence context (B4)
supplies the first adapter that actually means something — swapping it in
changes zero lines in ParcelService, Parcel, or any Registry test, which
is this boundary's whole point. `tenant_id`/`parcel_id` are accepted (per
ADR-019's amended signature) and deliberately unused here — a real adapter
uses them to verify ownership; this placeholder has no data to check them
against.

Not in app.contexts.registry.adapters.postgres_repositories: unlike
PostgresParcelRepository/PostgresParcelNumberAllocator, this adapter has
no session, no SQL, and no relationship to Postgres at all — keeping it in
its own module signals that geometry adapters are a different axis from
the Postgres/in-memory split used elsewhere in this context.
"""
from __future__ import annotations


class PlaceholderGeometryAdapter:
    async def reference_is_valid(
        self, *, geometry_reference: str, tenant_id: str, parcel_id: str
    ) -> bool:
        return True
