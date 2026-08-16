from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.agents.base import AgentRequest, BaseAgent
from app.agents.registry import agent_registry
from app.db.session import AsyncSessionLocal
from app.schemas.contact import ContactDiscoveryRequest
from app.schemas.company_intelligence import CompanyIntelligenceRequest
from app.schemas.email_personalization import EmailPersonalizationRequest
from app.lead_discovery.search import get_job_search_provider
from app.services.contact import ContactService
from app.services.company import CompanyService
from app.services.company_intelligence import CompanyIntelligenceService
from app.services.email_personalization import EmailPersonalizationService

logger = logging.getLogger(__name__)

class LeadDiscoveryAgent(BaseAgent):
    name = "lead_discovery"
    description = "Orchestrates discovering companies, extracting contacts, and drafting personalized emails."

    async def run(self, request: AgentRequest) -> dict[str, Any]:
        discovered_companies = []
        location = request.payload.get("location", "Mumbai").strip().title()
        work_mode = request.payload.get("work_mode", "remote")
        batch_size = request.payload.get("batch_size", 5)
        user_id = request.payload.get("user_id")

        if not user_id:
            logger.error(
                "Lead discovery called without user_id — aborting to prevent orphan contacts",
                extra={"action": "missing_user_id", "payload_keys": list(request.payload.keys())},
            )
            return {
                "status": "failed",
                "error": "user_id is required for lead discovery",
            }

        logger.info(
            "Searching for companies",
            extra={"action": "search_companies", "normalized_city": location, "work_mode": work_mode, "user_id": user_id}
        )
        search_provider = get_job_search_provider()
        try:
            leads = await search_provider.search_companies(location, work_mode)
            logger.info("Company leads discovered", extra={"action": "leads_discovered", "count": len(leads)})
            if not leads:
                return {
                    "status": "failed",
                    "error": "Company lead discovery failed"
                }
        except Exception as e:
            logger.error(f"Failed to search for companies: {e}", extra={"action": "search_failed", "error": str(e)})
            return {
                "status": "failed",
                "error": "Company lead discovery failed"
            }

        total_contacts_discovered = 0
        emails_drafted = 0
        processed_contacts = []

        async with AsyncSessionLocal() as session:
            user_uuid = UUID(user_id)
            logger.info(
                "Creating contact service with user_id",
                extra={"action": "contact_service_init", "user_id": str(user_uuid)},
            )
            contact_service = ContactService(session, user_id=user_uuid)
            company_service = CompanyService(session)
            company_intel_service = CompanyIntelligenceService(session)
            email_pers_service = EmailPersonalizationService(session)

            for lead in leads:
                if len(discovered_companies) >= batch_size:
                    break
                
                from app.core.redis import get_redis_client
                from sqlalchemy import select
                from app.models.user import User
                
                redis = get_redis_client()
                is_cancelled = await redis.get(f"task:cancel:{request.context.run_id}")
                if is_cancelled:
                    logger.info("Lead discovery task cancelled via API", extra={"action": "task_cancelled"})
                    break
                
                expected_token_version = request.context.metadata.get("token_version")
                if expected_token_version is not None:
                    user_record = (await session.execute(select(User).where(User.id == user_uuid))).scalar_one_or_none()
                    if not user_record or user_record.refresh_token_version != expected_token_version:
                        logger.info("User session invalidated, aborting lead discovery task", extra={"action": "session_invalidated"})
                        break
                
                company_name = lead.name
                url = lead.url

                # Discover contacts
                discovery_request = ContactDiscoveryRequest(
                    company_name=company_name,
                    source_urls=[url],
                    run_in_background=False,
                )
                
                try:
                    contacts = await contact_service.discover_now(discovery_request)
                    discovered_companies.append({
                        "name": company_name,
                        "url": url,
                        "contacts_count": len(contacts) if contacts else 0
                    })
                    logger.info("Contacts extracted and persisted", extra={
                        "action": "contacts_persisted",
                        "company_name": company_name,
                        "url": url,
                        "count": len(contacts) if contacts else 0
                    })
                except Exception as e:
                    logger.error(f"Failed to discover contacts for {url}: {e}", extra={"action": "contact_discovery_failed", "url": url, "error": str(e)})
                    # Still append the company even if discovery fails completely
                    discovered_companies.append({
                        "name": company_name,
                        "url": url,
                        "contacts_count": 0
                    })
                    continue

                for contact in contacts:
                    # Let the contact loop run for the discovered company to get all contacts for it, 
                    # or limit per company if needed. But we don't break early based on total_contacts_discovered.
                    
                    # Ensure company exists and get intelligence
                    company_id = contact.company_id
                    company_intel_id = None
                    if company_id:
                        # Ensure intelligence exists
                        intel_req = CompanyIntelligenceRequest(
                            company_id=company_id,
                            source_url=url,
                            run_in_background=False
                        )
                        try:
                            intel = await company_intel_service.analyze(intel_req)
                            company_intel_id = intel.id
                        except Exception as e:
                            logger.error(f"Failed to analyze company {company_id}: {e}")
                    
                    # Generate email draft
                    try:
                        # Template must be robust enough or provided by the UI. Since it's automated, we use a generic placeholder.
                        template = "Hi {name},\n\nI noticed {company_name} is hiring in {location}. {company_insights}\n\nI have experience in this space: {portfolio_links}.\n\nBest,\n[Your Name]"
                        email_req = EmailPersonalizationRequest(
                            template_content=template,
                            template_name="Automated Discovery Template",
                            contact_id=contact.id,
                            company_intelligence_id=company_intel_id,
                            user_id=user_id,
                            save_draft=True,
                            run_in_background=False,
                            custom_instructions="Keep it concise and professional. Do not invent a resume link."
                        )
                        await email_pers_service.generate(email_req)
                        emails_drafted += 1
                        total_contacts_discovered += 1
                        processed_contacts.append(str(contact.id))
                    except Exception as e:
                        logger.error(f"Failed to generate email for contact {contact.id}: {e}")

        logger.info("Lead discovery task completed", extra={
            "action": "lead_discovery_completed",
            "contacts_discovered": total_contacts_discovered,
            "emails_drafted": emails_drafted,
            "processed_contact_ids": processed_contacts
        })

        return {
            "status": "completed",
            "contacts_discovered": total_contacts_discovered,
            "emails_drafted": emails_drafted,
            "processed_contact_ids": processed_contacts,
            "discovered_companies": discovered_companies,
            "location": location,
        }

def register_lead_discovery_agent() -> None:
    if "lead_discovery" not in agent_registry.names():
        agent_registry.register(LeadDiscoveryAgent())
