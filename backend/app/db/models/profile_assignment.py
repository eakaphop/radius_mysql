"""app_profile_assignments: which group/user a bandwidth profile was applied to.

Not listed in CLAUDE.md 4.2, but GET /shaping/profiles/{id}/targets and the
"re-apply to every target" prompt need a record of it, and it can't be
inferred reliably from radreply/radgroupreply values — see docs/decisions.md.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class AppProfileAssignment(Base):
    __tablename__ = "app_profile_assignments"
    __table_args__ = (
        UniqueConstraint("target_type", "target_name", name="uq_app_profile_assignments_target"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("app_bandwidth_profiles.id"), nullable=False, index=True
    )
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target_name: Mapped[str] = mapped_column(String(64), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    applied_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("app_admin_users.id"), nullable=False
    )
