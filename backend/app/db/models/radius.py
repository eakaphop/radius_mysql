"""ORM models for the existing FreeRADIUS tables (read/write data, never DDL)."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.freeradius_base import FreeradiusBase


class RadCheck(FreeradiusBase):
    __tablename__ = "radcheck"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    attribute: Mapped[str] = mapped_column(String(64), nullable=False)
    op: Mapped[str] = mapped_column(String(2), nullable=False)
    value: Mapped[str] = mapped_column(String(253), nullable=False)


class RadReply(FreeradiusBase):
    __tablename__ = "radreply"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    attribute: Mapped[str] = mapped_column(String(64), nullable=False)
    op: Mapped[str] = mapped_column(String(2), nullable=False)
    value: Mapped[str] = mapped_column(String(253), nullable=False)


class RadUserGroup(FreeradiusBase):
    __tablename__ = "radusergroup"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    groupname: Mapped[str] = mapped_column(String(64), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class RadGroupCheck(FreeradiusBase):
    __tablename__ = "radgroupcheck"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    groupname: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    attribute: Mapped[str] = mapped_column(String(64), nullable=False)
    op: Mapped[str] = mapped_column(String(2), nullable=False)
    value: Mapped[str] = mapped_column(String(253), nullable=False)


class RadGroupReply(FreeradiusBase):
    __tablename__ = "radgroupreply"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    groupname: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    attribute: Mapped[str] = mapped_column(String(64), nullable=False)
    op: Mapped[str] = mapped_column(String(2), nullable=False)
    value: Mapped[str] = mapped_column(String(253), nullable=False)


class RadAcct(FreeradiusBase):
    """Accounting records. Large table — always filter and paginate.

    `groupname` is deliberately NOT mapped: the standard schema doesn't have
    it, and this project's target DB confirmed `Unknown column
    'radacct.groupname'` when it was.
    """

    __tablename__ = "radacct"

    radacctid: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    acctsessionid: Mapped[str] = mapped_column(String(64), nullable=False)
    acctuniqueid: Mapped[str] = mapped_column(String(32), nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    nasipaddress: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    nasportid: Mapped[str | None] = mapped_column(String(32), nullable=True)
    nasporttype: Mapped[str | None] = mapped_column(String(32), nullable=True)
    acctstarttime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    acctupdatetime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acctstoptime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    acctsessiontime: Mapped[int | None] = mapped_column(Integer, nullable=True)
    acctinputoctets: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    acctoutputoctets: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    calledstationid: Mapped[str | None] = mapped_column(String(50), nullable=True)
    callingstationid: Mapped[str | None] = mapped_column(String(50), nullable=True)
    acctterminatecause: Mapped[str | None] = mapped_column(String(32), nullable=True)
    servicetype: Mapped[str | None] = mapped_column(String(32), nullable=True)
    framedprotocol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    framedipaddress: Mapped[str | None] = mapped_column(String(15), nullable=True)


class RadPostAuth(FreeradiusBase):
    """Authentication results.

    The `pass` column is deliberately NOT mapped: it can contain the password
    the client submitted, which must never leave the database (CLAUDE.md 8).
    The default schema has no NAS column — see docs/decisions.md.
    """

    __tablename__ = "radpostauth"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reply: Mapped[str] = mapped_column(String(32), nullable=False)
    authdate: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Nas(FreeradiusBase):
    """NAS clients. Unmapped columns (ports, server, community, ...) keep their
    database defaults on insert."""

    __tablename__ = "nas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nasname: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    shortname: Mapped[str | None] = mapped_column(String(32), nullable=True)
    type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    secret: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
