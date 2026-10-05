"""Separate declarative base for existing FreeRADIUS tables (radcheck, ...).

These are NEVER managed by Alembic (see alembic/env.py, which only points at
`app.db.models.base.Base.metadata`) — CLAUDE.md forbids migrations that touch
the FreeRADIUS schema. Keeping them on a different Base means an `alembic
revision --autogenerate` can never propose CREATE/ALTER/DROP for them, even
by accident. Column widths below follow the FreeRADIUS 3.x default MySQL
schema; verify against the real target schema once docs/freeradius-schema.sql
is filled in (see docs/environment.md).
"""

from sqlalchemy.orm import DeclarativeBase


class FreeradiusBase(DeclarativeBase):
    pass
