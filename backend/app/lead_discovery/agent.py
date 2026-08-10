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
        location = request.payload.get("location", "Mumbai")
        work_mode = request.payload.get("work_mode", "remote")
        batch_size = request.payload.get("batch_size", 5)
        user_id = request.payload.get("user_id")

        # 1. Search for public company URLs
        search_provider = get_job_search_provider()
        try:
            urls = await search_provider.search_companies(location, work_mode)
        except Exception as e:
            logger.error(f"Failed to search for companies: {e}")
            urls = []

        total_contacts_discovered = 0
        emails_drafted = 0
        processed_contacts = []

        async with AsyncSessionLocal() as session:
            contact_service = ContactService(session)
            company_service = CompanyService(session)
            company_intel_service = CompanyIntelligenceService(session)
            email_pers_service = EmailPersonalizationService(session)

            for url in urls:
                if total_contacts_discovered >= batch_size:
                    break
                
                # Use domain as fallback company name
                domain = url.split("//")[-1].split("/")[0].replace("www.", "")
                company_name = domain.split(".")[0].capitalize()

                # Discover contacts
                discovery_request = ContactDiscoveryRequest(
                    company_name=company_name,
                    source_urls=[url],
                    run_in_background=False,
                )
                
                try:
                    contacts = await contact_service.discover_now(discovery_request)
                except Exception as e:
                    logger.error(f"Failed to discover contacts for {url}: {e}")
                    continue

                for contact in contacts:
                    if total_contacts_discovered >= batch_size:
                        break
                    
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

        return {
            "status": "completed",
            "contacts_discovered": total_contacts_discovered,
            "emails_drafted": emails_drafted,
            "processed_contact_ids": processed_contacts,
        }

def register_lead_discovery_agent() -> None:
    if "lead_discovery" not in agent_registry.names():
        agent_registry.register(LeadDiscoveryAgent())
