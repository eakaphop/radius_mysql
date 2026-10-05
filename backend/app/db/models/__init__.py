from app.db.models.admin_user import AdminRole, AppAdminUser
from app.db.models.audit_log import AppAuditLog
from app.db.models.bandwidth_profile import AppBandwidthProfile, ProfileServiceType
from app.db.models.base import Base
from app.db.models.freeradius_base import FreeradiusBase
from app.db.models.profile_assignment import AppProfileAssignment
from app.db.models.radius import (
    Nas,
    RadAcct,
    RadCheck,
    RadGroupCheck,
    RadGroupReply,
    RadPostAuth,
    RadReply,
    RadUserGroup,
)
from app.db.models.refresh_token import AppRefreshToken

__all__ = [
    # app_* tables (managed by Alembic)
    "Base",
    "AdminRole",
    "AppAdminUser",
    "AppRefreshToken",
    "AppAuditLog",
    "AppBandwidthProfile",
    "ProfileServiceType",
    "AppProfileAssignment",
    # FreeRADIUS tables (data only, never migrated)
    "FreeradiusBase",
    "RadCheck",
    "RadReply",
    "RadUserGroup",
    "RadGroupCheck",
    "RadGroupReply",
    "RadAcct",
    "RadPostAuth",
    "Nas",
]
