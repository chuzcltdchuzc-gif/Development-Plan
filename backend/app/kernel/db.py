"""Shared SQLAlchemy declarative base and session factory.

One Base across all bounded contexts so Alembic's autogenerate can see every
context's models from a single `target_metadata` (migrations/env.py).
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
