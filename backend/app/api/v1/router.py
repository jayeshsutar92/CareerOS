from fastapi import APIRouter, Depends

from app.api.deps import enforce_rate_limit
from app.api.v1.auth import router as auth_router
from app.api.v1.companies import router as companies_router
from app.api.v1.company_intelligence import router as company_intelligence_router
from app.api.v1.contacts import router as contacts_router
from app.api.v1.email_personalization import router as email_personalization_router
from app.api.v1.email_delivery import router as email_delivery_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.lead_discovery import router as lead_discovery_router
from app.api.v1.tasks import router as tasks_router

api_router = APIRouter(dependencies=[Depends(enforce_rate_limit)])
api_router.include_router(auth_router)
api_router.include_router(companies_router)
api_router.include_router(company_intelligence_router)
api_router.include_router(contacts_router)
api_router.include_router(email_personalization_router)
api_router.include_router(email_delivery_router, prefix="/emails", tags=["emails"])
api_router.include_router(jobs_router)
api_router.include_router(lead_discovery_router)
api_router.include_router(tasks_router)
api_router.include_router(health_router)


