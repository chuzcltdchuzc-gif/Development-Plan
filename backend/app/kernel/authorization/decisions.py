"""Authorization decision types — Decision, Obligation, Effect."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Effect(StrEnum):
    PERMIT = "PERMIT"
    DENY = "DENY"


@dataclass(frozen=True)
class Obligation:
    """A constraint the caller must apply on a permitted response
    (e.g. field projection, masking, audit-only-mode)."""

    kind: str
    args: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Decision:
    effect: Effect
    reason: str
    obligations: tuple[Obligation, ...] = field(default_factory=tuple)
    policy_id: str | None = None

    @property
    def permitted(self) -> bool:
        return self.effect == Effect.PERMIT

    @classmethod
    def permit(
        cls,
        reason: str = "permitted",
        policy_id: str | None = None,
        obligations: list[Obligation] | None = None,
    ) -> Decision:
        return cls(
            effect=Effect.PERMIT,
            reason=reason,
            policy_id=policy_id,
            obligations=tuple(obligations or ()),
        )

    @classmethod
    def deny(cls, reason: str = "denied", policy_id: str | None = None) -> Decision:
        return cls(effect=Effect.DENY, reason=reason, policy_id=policy_id)
