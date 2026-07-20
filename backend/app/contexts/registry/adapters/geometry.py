"""Placeholder GeometryPort adapter (B3 slice 4, docs/adr/ADR-016).

Deliberately not a feature: `reference_is_valid` always returns `True`,
validating nothing about the reference's content. This exists so Registry
can be wired, tested, and deployed today with a functioning
dependency-injection seam ("ports before adapters") without depending on
any GIS infrastructure. A future Spatial Intelligence context (B4)
supplies the first adapter that actually means something — swapping it in
changes zero lines in ParcelService, Parcel, or any Registry test, which
is this boundary's whole point.

Not in app.contexts.registry.adapters.postgres_repositories: unlike
PostgresParcelRepository/PostgresParcelNumberAllocator, this adapter has
no session, no SQL, and no relationship to Postgres at all — keeping it in
its own module signals that geometry adapters are a different axis from
the Postgres/in-memory split used elsewhere in this context.
"""
from __future__ import annotations


class PlaceholderGeometryAdapter:
    async def reference_is_valid(self, *, geometry_reference: str) -> bool:
        return True
