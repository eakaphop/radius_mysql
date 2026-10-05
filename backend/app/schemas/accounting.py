"""Pydantic schemas for /accounting (and radacct rows reused elsewhere)."""

from pydantic import BaseModel

from app.utils.timezones import RadiusDateTime


class AccountingItem(BaseModel):
    radacctid: int
    acctsessionid: str
    username: str | None
    nasipaddress: str
    nasporttype: str | None
    framedipaddress: str | None
    callingstationid: str | None
    acctstarttime: RadiusDateTime | None
    acctstoptime: RadiusDateTime | None
    acctsessiontime: int | None
    acctinputoctets: int | None
    acctoutputoctets: int | None
    acctterminatecause: str | None

    model_config = {"from_attributes": True}


class AccountingDetail(AccountingItem):
    acctuniqueid: str
    nasportid: str | None
    calledstationid: str | None
    servicetype: str | None
    framedprotocol: str | None
    acctupdatetime: RadiusDateTime | None
