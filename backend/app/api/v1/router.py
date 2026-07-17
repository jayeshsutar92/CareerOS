from fastapi import APIRouter, Depends

from app.api.deps import enforce_rate_limit
from app.api.v1.auth import router as auth_router
from app.api.v1.companies import router as companies_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router

api_router = APIRouter(dependencies=[Depends(enforce_rate_limit)])
api_router.include_router(auth_router)
api_router.include_router(companies_router)
api_router.include_router(jobs_router)
api_router.include_router(health_router)
