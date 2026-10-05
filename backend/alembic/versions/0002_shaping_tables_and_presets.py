"""create app_bandwidth_profiles, app_profile_assignments; seed presets

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-13
"""

from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    profiles = op.create_table(
        "app_bandwidth_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column(
            "service_type",
            sa.Enum("pppoe", "hotspot", "both", native_enum=False, length=16),
            nullable=False,
            server_default="both",
        ),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("download_kbps", sa.Integer(), nullable=True),
        sa.Column("upload_kbps", sa.Integer(), nullable=True),
        sa.Column("burst_download_kbps", sa.Integer(), nullable=True),
        sa.Column("burst_upload_kbps", sa.Integer(), nullable=True),
        sa.Column("burst_threshold_download_kbps", sa.Integer(), nullable=True),
        sa.Column("burst_threshold_upload_kbps", sa.Integer(), nullable=True),
        sa.Column("burst_time_sec", sa.Integer(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("min_download_kbps", sa.Integer(), nullable=True),
        sa.Column("min_upload_kbps", sa.Integer(), nullable=True),
        sa.Column("session_timeout_sec", sa.Integer(), nullable=True),
        sa.Column("idle_timeout_sec", sa.Integer(), nullable=True),
        sa.Column("simultaneous_use", sa.Integer(), nullable=True),
        sa.Column("mikrotik_group", sa.String(length=64), nullable=True),
        sa.Column("framed_pool", sa.String(length=64), nullable=True),
        sa.Column("total_quota_bytes", sa.BigInteger(), nullable=True),
        sa.Column("address_list", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("name", name="uq_app_bandwidth_profiles_name"),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )

    op.create_table(
        "app_profile_assignments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "profile_id",
            sa.Integer(),
            sa.ForeignKey("app_bandwidth_profiles.id"),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(length=16), nullable=False),
        sa.Column("target_name", sa.String(length=64), nullable=False),
        sa.Column("applied_at", sa.DateTime(), nullable=False),
        sa.Column(
            "applied_by",
            sa.Integer(),
            sa.ForeignKey("app_admin_users.id"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "target_type", "target_name", name="uq_app_profile_assignments_target"
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_app_profile_assignments_profile_id", "app_profile_assignments", ["profile_id"]
    )

    now = datetime.utcnow()

    def preset(
        name: str,
        service_type: str,
        description: str,
        download_kbps: int | None,
        upload_kbps: int | None,
        *,
        simultaneous_use: int | None = None,
        idle_timeout_sec: int | None = None,
    ) -> dict[str, object]:
        return {
            "name": name,
            "service_type": service_type,
            "description": description,
            "download_kbps": download_kbps,
            "upload_kbps": upload_kbps,
            "priority": 8,
            "simultaneous_use": simultaneous_use,
            "idle_timeout_sec": idle_timeout_sec,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }

    # Presets from CLAUDE.md 6.1: Basic 10/5, Standard 30/10, Premium 100/50
    # (download/upload, Mbps) per service, plus Unlimited with no Rate-Limit.
    op.bulk_insert(
        profiles,
        [
            preset("pppoe-basic", "pppoe", "PPPoE Basic 10/5 Mbps", 10000, 5000, simultaneous_use=1),
            preset(
                "pppoe-standard", "pppoe", "PPPoE Standard 30/10 Mbps", 30000, 10000,
                simultaneous_use=1,
            ),
            preset(
                "pppoe-premium", "pppoe", "PPPoE Premium 100/50 Mbps", 100000, 50000,
                simultaneous_use=1,
            ),
            preset(
                "hotspot-basic", "hotspot", "Hotspot Basic 10/5 Mbps", 10000, 5000,
                simultaneous_use=2, idle_timeout_sec=600,
            ),
            preset(
                "hotspot-standard", "hotspot", "Hotspot Standard 30/10 Mbps", 30000, 10000,
                simultaneous_use=3, idle_timeout_sec=600,
            ),
            preset(
                "hotspot-premium", "hotspot", "Hotspot Premium 100/50 Mbps", 100000, 50000,
                simultaneous_use=5, idle_timeout_sec=900,
            ),
            preset("unlimited", "both", "Unlimited (no Mikrotik-Rate-Limit)", None, None),
        ],
    )


def downgrade() -> None:
    op.drop_table("app_profile_assignments")
    op.drop_table("app_bandwidth_profiles")
