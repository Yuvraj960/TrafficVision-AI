from fastapi import APIRouter

from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.violations import router as violations_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router

v1_router = APIRouter()

v1_router.include_router(auth_router, tags=["Auth"])
v1_router.include_router(ingestion_router, tags=["Ingestion"])
v1_router.include_router(violations_router, tags=["Violations"])
v1_router.include_router(analytics_router, tags=["Analytics"])
