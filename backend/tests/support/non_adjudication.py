"""Ownership-adjudication wording scanner (Engineering Rules #10, LV-000 v1.8 Article IV §4).

Test-support utility, not application code — deliberately lives under `tests/`, not `app/`,
because it is a CI-time verification mechanism (`docs/PHASE-9_IMPLEMENTATION_PLAN.md` §10), not
runtime behaviour. Two independent scanning layers, per the plan:

- `collect_static_sites` / `scan_static_sources`: AST-based extraction of developer-authored
  string literals from specific constructs only — `HTTPException(..., detail=...)` calls anywhere
  under `app/`, any `description=` keyword argument anywhere under `app/` (Pydantic `Field`,
  route/DTO metadata), and docstrings (module/class/function) *only* within `api/` directories,
  since those are the ones FastAPI actually surfaces via OpenAPI. Internal application/domain-layer
  docstrings are deliberately excluded — this codebase's own architectural commentary discusses
  "ownership", "determination", and "adjudication" as concepts extensively (see e.g.
  `app/contexts/registry/domain/history.py`'s module docstring), and none of that prose is ever
  returned to an API caller. Scanning it would be a false-positive generator with no constitutional
  basis (`docs/PHASE-9_IMPLEMENTATION_PLAN.md` §6.2).
- `scan_response_text`: flattens a JSON-serializable payload (an actual API response body) to text
  and scans it — catches wording assembled at runtime that a pure source scan would miss
  (`docs/PHASE-9_IMPLEMENTATION_PLAN.md` §6.7).

Both layers share one blocklist and one matching function (`find_violations`) so the boundary is
defined once, not duplicated.

`ADJUDICATION_PHRASES` is deliberately **multi-word phrases expressing a determination-of-right
claim** — never bare single words like "owner", "confirmed", "verified", or "conflict" in
isolation. Single words are legitimate elsewhere in this codebase: `current_owner_name` as a field
identifier (ADR-013 invariant #12 — a reference, never a determination), ADR-021's six-category
spatial classification vocabulary ("confirmed conflict" — a geometric finding, not an ownership
determination, per that ADR's own §5), and Platform Intelligence's advisory "signal"/"verified"
language (`docs/PLATFORM_INTELLIGENCE_ARCHITECTURE.md`). See
`docs/PHASE-9_IMPLEMENTATION_PLAN.md` §6.6 and §12 for the full false-positive reasoning this list
is designed against.

This list is reviewable and amendable through normal PR review (§12 of the plan) — it is not
claimed to be exhaustive; Article IV §4's "mechanically enforced" standard is a floor, not a claim
that no novel phrasing could ever slip past a keyword-based check (§6.7, §13 of the plan).
"""
from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ADJUDICATION_PHRASES: tuple[str, ...] = (
    "confirmed owner",
    "confirmed as owner",
    "confirmed as the owner",
    "confirmed as its owner",
    "verified owner",
    "verified as owner",
    "verified as the owner",
    "rightful owner",
    "true owner",
    "real owner",
    "actual owner",
    "the legal owner",
    "legal owner of",
    "legally owns",
    "officially owns",
    "is the owner of this",
    "owns this parcel",
    "owner of record confirmed",
    "confirmed ownership",
    "confirms ownership",
    "ownership is confirmed",
    "ownership has been confirmed",
    "ownership has been determined",
    "ownership is determined",
    "determined ownership",
    "determined the owner",
    "determined to be the owner",
    "title is confirmed",
    "title has been confirmed",
    "title is valid",
    "valid title",
    "confirms title",
    "confirms clear title",
    "resolves the ownership",
    "resolves this claim",
    "resolves the claim",
    "wins the claim",
    "wins the dispute",
    "invalidates the claim",
    "adjudicated ownership",
    "adjudicates ownership",
    "landvault has determined",
    "landvault confirms ownership",
    "landvault has verified ownership",
)


def find_violations(text: str) -> list[str]:
    """Case-insensitive substring match against `ADJUDICATION_PHRASES`. Returns the matched
    phrases (empty list means no violation)."""
    lowered = text.lower()
    return [phrase for phrase in ADJUDICATION_PHRASES if phrase in lowered]


@dataclass(frozen=True)
class StaticStringSite:
    file: Path
    line: int
    kind: str  # "http_exception_detail" | "field_description" | "api_docstring"
    text: str


def _string_value(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        # f-string — collect only its literal segments; a fully dynamic
        # f-string contributes no literal text to scan, which is a known,
        # documented limitation (plan §6.7), not silently pretended away.
        parts = [
            seg.value
            for seg in node.values
            if isinstance(seg, ast.Constant) and isinstance(seg.value, str)
        ]
        return "".join(parts) if parts else None
    return None


def _iter_python_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def collect_static_sites(root: Path) -> list[StaticStringSite]:
    """Walk every `.py` file under `root` and extract the string sites §10 must check:
    `HTTPException(detail=...)` calls, any `description=` keyword argument, and — only for files
    inside an `api/` directory — module/class/function docstrings."""
    sites: list[StaticStringSite] = []

    for path in _iter_python_files(root):
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue

        in_api_dir = "api" in path.parts

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                func_name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
                for kw in node.keywords:
                    if kw.arg == "detail" and func_name == "HTTPException":
                        value = _string_value(kw.value)
                        if value:
                            sites.append(
                                StaticStringSite(path, node.lineno, "http_exception_detail", value)
                            )
                    elif kw.arg == "description":
                        value = _string_value(kw.value)
                        if value:
                            sites.append(
                                StaticStringSite(path, node.lineno, "field_description", value)
                            )

            if in_api_dir and isinstance(
                node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            ):
                doc = ast.get_docstring(node, clean=False)
                if doc:
                    line = getattr(node, "lineno", 1)
                    sites.append(StaticStringSite(path, line, "api_docstring", doc))

    return sites


def scan_static_sources(root: Path) -> list[tuple[StaticStringSite, list[str]]]:
    """Returns `(site, matched_phrases)` for every extracted site that violates the blocklist."""
    hits: list[tuple[StaticStringSite, list[str]]] = []
    for site in collect_static_sites(root):
        violations = find_violations(site.text)
        if violations:
            hits.append((site, violations))
    return hits


def scan_response_text(payload: Any) -> list[str]:
    """Flattens a JSON-serializable API response payload to text and scans it for blocklisted
    phrases — the runtime counterpart to `scan_static_sources`, catching wording assembled at
    request time that a pure source scan cannot see (plan §6.7)."""
    text = json.dumps(payload, default=str)
    return find_violations(text)
