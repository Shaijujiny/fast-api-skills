"""Router registry: every feature router is mounted here."""

from fastapi import APIRouter

from app.api.auth.router import router as auth_router
from app.api.health.router import router as health_router
from app.api.roles.router import router as roles_router
from app.api.users.router import router as users_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(roles_router)
