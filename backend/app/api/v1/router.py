"""Aggregates all /api/v1 routers."""

from fastapi import APIRouter

from app.api.v1.accounting import router as accounting_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.groups import router as groups_router
from app.api.v1.nas import router as nas_router
from app.api.v1.postauth import router as postauth_router
from app.api.v1.sessions import router as sessions_router
from app.api.v1.shaping import router as shaping_router
from app.api.v1.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(groups_router)
api_router.include_router(nas_router)
api_router.include_router(shaping_router)
api_router.include_router(accounting_router)
api_router.include_router(sessions_router)
api_router.include_router(postauth_router)
api_router.include_router(dashboard_router)
api_router.include_router(audit_router)
