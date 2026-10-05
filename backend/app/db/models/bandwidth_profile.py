"""app_bandwidth_profiles: reusable MikroTik shaping profiles (CLAUDE.md 4.2 / 6.1)."""

import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class ProfileServiceType(str, enum.Enum):
    pppoe = "pppoe"
    hotspot = "hotspot"
    both = "both"


class AppBandwidthProfile(Base):
    __tablename__ = "app_bandwidth_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    service_type: Mapped[ProfileServiceType] = mapped_column(
        Enum(ProfileServiceType, native_enum=False, length=16),
        nullable=False,
        default=ProfileServiceType.both,
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    download_kbps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    upload_kbps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    burst_download_kbps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    burst_upload_kbps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    burst_threshold_download_kbps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    burst_threshold_upload_kbps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    burst_time_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    min_download_kbps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_upload_kbps: Mapped[int | None] = mapped_column(Integer, nullable=True)

    session_timeout_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    idle_timeout_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    simultaneous_use: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mikrotik_group: Mapped[str | None] = mapped_column(String(64), nullable=True)
    framed_pool: Mapped[str | None] = mapped_column(String(64), nullable=True)
    total_quota_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    address_list: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Name of a Bandwidth Profile pre-created in the UniFi Network Controller
    # (Settings > Profiles > Bandwidth Profiles) — UniFi has no RADIUS VSA for
    # rate limits, it looks up the limits locally by this Filter-Id (CLAUDE.md
    # 6.1 / docs/decisions.md "UniFi traffic shaping via Filter-Id").
    unifi_filter_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
