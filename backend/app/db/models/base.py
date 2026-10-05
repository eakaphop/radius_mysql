"""Shared SQLAlchemy declarative base.

Per-table models (radcheck, radreply, app_admin_users, ...) are added in
their own files here as each feature phase implements them.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
