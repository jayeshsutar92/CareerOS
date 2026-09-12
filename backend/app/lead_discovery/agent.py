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
from app.lead_discovery.metrics import DiscoveryMetrics
from app.lead_discovery.models import CompanyCandidateSet
from app.lead_discovery.search import CompanyLead
import asyncio

logger = logging.getLogger(__name__)

class LeadDiscoveryAgent(BaseAgent):
    name = "lead_discovery"
    description = "Orchestrates discovering companies, extracting contacts, and drafting personalized emails."

    async def run(self, request: AgentRequest) -> dict[str, Any]:
        metrics = DiscoveryMetrics()
        discovered_companies = []
        job_role = request.payload.get("job_role")
        if isinstance(job_role, str):
            job_role = job_role.strip()
            
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
            extra={"action": "search_companies", "job_role": job_role, "normalized_city": location, "work_mode": work_mode, "user_id": user_id}
        )
        search_provider = get_job_search_provider()
        try:
            with metrics.measure_stage("company_search_and_resolution"):
                # Phase 1: Multi-Source Company Discovery
                candidate_set: CompanyCandidateSet = await search_provider.search_companies(job_role, location, work_mode, batch_size, metrics=metrics)
                
                # Phase 2: Entity Resolution (Authoritative Normalization & Clustering)
                from app.lead_discovery.entity_resolver import EntityResolver
                resolver = EntityResolver(min_confidence=40)
                resolved_entities = resolver.resolve_entities(candidate_set, location)
                
                top_entities = resolved_entities[:batch_size * 2] if batch_size else resolved_entities
                
                # Phase 3: Website Candidate Resolution
                from app.lead_discovery.website_resolver import WebsiteResolver
                web_resolver = WebsiteResolver(min_confidence=40)
                
                resolve_tasks = [web_resolver.resolve_website(entity, metrics=metrics) for entity in top_entities]
                resolved_entities_with_web = await asyncio.gather(*resolve_tasks, return_exceptions=True)
                
                valid_entities = [e for e in resolved_entities_with_web if isinstance(e, CanonicalCompanyEntity) and e.website_evidence and e.website_evidence.selected_url]
                
                # Phase 4: Evidence Collection
                from app.lead_discovery.evidence_collector import EvidenceCollector
                evidence_collector = EvidenceCollector()
                
                evidence_tasks = [evidence_collector.collect(entity, metrics=metrics) for entity in valid_entities]
                collected_evidences = await asyncio.gather(*evidence_tasks, return_exceptions=True)
                
                # Zip the successful evidence collections back to the entities
                valid_entities_with_evidence = []
                for entity, ev_result in zip(valid_entities, collected_evidences):
                    if not isinstance(ev_result, Exception):
                        valid_entities_with_evidence.append((entity, ev_result))
                
                # Phase 5: Social Resolution
                from app.lead_discovery.social_resolver import SocialResolver
                soc_resolver = SocialResolver(min_confidence=40)
                
                social_tasks = [soc_resolver.resolve_socials(entity, ev_dict, metrics=metrics) for entity, ev_dict in valid_entities_with_evidence]
                resolved_social_evidences = await asyncio.gather(*social_tasks, return_exceptions=True)
                
                valid_entities_with_socials = []
                for (entity, ev_dict), soc_ev in zip(valid_entities_with_evidence, resolved_social_evidences):
                    if not isinstance(soc_ev, Exception):
                        valid_entities_with_socials.append((entity, ev_dict, soc_ev))
                
                # Phase 6: Careers Surface Discovery
                from app.lead_discovery.careers_resolver import CareersResolver
                careers_resolver = CareersResolver()
                
                careers_tasks = [careers_resolver.resolve_careers(entity, ev_dict, soc_ev, metrics=metrics) for entity, ev_dict, soc_ev in valid_entities_with_socials]
                resolved_careers_surfaces = await asyncio.gather(*careers_tasks, return_exceptions=True)
                
                valid_entities_full = []
                for (entity, ev_dict, soc_ev), car_ev in zip(valid_entities_with_socials, resolved_careers_surfaces):
                    if not isinstance(car_ev, Exception):
                        valid_entities_full.append((entity, ev_dict, soc_ev, car_ev))
                
                # --- BACKWARD COMPATIBILITY ADAPTER ---
                # Convert CanonicalCompanyEntity to legacy CompanyLead to feed downstream Contact Discovery / Verification
                legacy_leads = []
                for entity, ev_dict, soc_ev, car_ev in valid_entities_full:
                    provider = " | ".join(list(set(e.provider for e in entity.evidence)))
                    
                    lead = CompanyLead(
                        name=entity.best_original_name,
                        url=entity.website_evidence.selected_url,
                        source_score=entity.aggregate_score,
                        source_name=provider,
                        is_official_resolved=True
                    )
                    lead.website_confidence = entity.website_evidence.confidence
                    lead.resolution_evidence["website_candidates"] = [c.url for c in entity.website_evidence.candidate_set.get_ranked_valid_candidates()][:3]
                    if entity.website_evidence.ai_arbitration_used:
                        lead.resolution_evidence["website_ai_adj"] = "ai_arbitrated"
                        
                    lead.resolution_evidence["collected_evidence"] = ev_dict
                    
                    # Attach social profiles to legacy lead
                    for platform, profile_url in soc_ev.resolved_profiles.items():
                        lead.socials[platform] = profile_url
                        
                    # Inject careers surfaces into legacy lead
                    lead.resolution_evidence["careers_surfaces"] = [
                        {"url": c.url, "type": c.surface_type, "method": c.discovery_method} 
                        for c in car_ev.candidates if not c.is_rejected
                    ]
                        
                    legacy_leads.append(lead)
                
                leads = legacy_leads[:batch_size]
                # --- END ADAPTER ---
                
            logger.info("Company leads discovered and resolved", extra={"action": "leads_discovered", "count": len(leads)})
            if not leads:
                return {
                    "status": "failed",
                    "error": "Company lead discovery failed"
                }
        except Exception as e:
            logger.exception("Failed to search for companies", extra={"action": "search_failed", "error": str(e)})
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
                from app.schemas.company import CompanyCreate
                from fastapi import HTTPException
                
                redis = get_redis_client()
                is_cancelled = await redis.get(f"task:cancel:{request.context.user_id}:{request.context.run_id}")
                if is_cancelled:
                    logger.info("Lead discovery task cancelled via API", extra={"action": "task_cancelled"})
                    active_task = await redis.get(f"active_discovery:{request.context.user_id}")
                    if active_task:
                        active_task_str = active_task.decode() if isinstance(active_task, bytes) else active_task
                        if active_task_str == request.context.run_id:
                            await redis.delete(f"active_discovery:{request.context.user_id}")
                            logger.info("Cleared active discovery task tracker on cancel", extra={"action": "tracker_cleared_cancel"})
                    break
                
                expected_token_version = request.context.metadata.get("token_version")
                if expected_token_version is not None:
                    user_record = (await session.execute(select(User).where(User.id == user_uuid))).scalar_one_or_none()
                    if not user_record or user_record.refresh_token_version != expected_token_version:
                        logger.info("User session invalidated, aborting lead discovery task", extra={"action": "session_invalidated"})
                        break
                
                company_name = lead.name
                url = lead.url
                
                logger.info("Company received", extra={"action": "company_received", "company_name": company_name})

                # 1. Safely get or create Company
                company_id = None
                try:
                    company = await company_service.create(CompanyCreate(name=company_name, website_url=url, description=""))
                    company_id = company.id
                    logger.info("Company created successfully", extra={"action": "company_created", "company_name": company_name})
                except HTTPException as e:
                    if e.status_code == 409:
                        # Find existing
                        logger.info("Company already exists", extra={"action": "company_exists", "company_name": company_name})
                        try:
                            company = await company_service.repository.get_by_name(company_name)
                            if not company:
                                company = await company_service.repository.get_by_website_url(url)
                            if company:
                                company_id = company.id
                        except Exception:
                            pass
                
                logger.info("Website resolved", extra={"action": "website_resolved", "company_id": str(company_id) if company_id else None, "url": url})
                logger.info("Company processed", extra={"action": "company_processed", "company_id": str(company_id) if company_id else None})
                
                # 2. Extract Company Intelligence for EVERY discovered company
                company_intel_id = None
                if company_id:
                    try:
                        intel_req = CompanyIntelligenceRequest(
                            company_id=company_id,
                            website_url=url,
                            company_name=company_name,
                            run_in_background=False
                        )
                        logger.info("Company Intelligence started", extra={"action": "intelligence_started", "company_id": str(company_id), "website_url": url})
                        intel_resp = await company_intel_service.analyze(intel_req, user_id=user_uuid)
                        if intel_resp.data:
                            company_intel_id = intel_resp.data.id
                        logger.info("Company intelligence crawled and persisted", extra={"action": "intelligence_crawled", "intel_id": str(company_intel_id)})
                    except Exception as e:
                        logger.error(f"Failed to analyze company {company_name}: {e}", extra={"action": "intelligence_failed", "error": str(e)})

                # 3. Discover contacts
                logger.info("Discovery started", extra={"action": "discovery_started", "company_name": company_name, "company_id": str(company_id)})
                discovery_request = ContactDiscoveryRequest(
                    company_name=company_name,
                    source_urls=[url],
                    company_id=company_id,
                    run_in_background=False,
                )
                
                try:
                    with metrics.measure_stage("contact_discovery"):
                        contacts = await contact_service.discover_now(discovery_request, metrics=metrics)
                    logger.info("Discovery completed", extra={
                        "action": "discovery_completed",
                        "company_name": company_name,
                        "url": url,
                        "count": len(contacts) if contacts else 0
                    })
                except Exception as e:
                    logger.error(f"Failed to discover contacts for {url}: {e}", extra={"action": "contact_discovery_failed", "url": url, "error": str(e)})
                    contacts = []
                
                company_contacts = []
                for contact in contacts:
                    company_contacts.append({
                        "id": str(contact.id),
                        "name": contact.name,
                        "role": contact.role,
                        "role_category": contact.role_category,
                        "confidence_score": contact.confidence_score,
                        "source_url": contact.source_url,
                        "contact_methods": contact.contact_methods,
                        "discovery_evidence": contact.discovery_evidence
                    })
                    total_contacts_discovered += 1
                    processed_contacts.append(str(contact.id))
                    
                # Phase 4: Verification & Confidence
                from app.lead_discovery.verification import VerificationStage
                verification_stage = VerificationStage()
                verified_company = verification_stage.verify(lead, company_contacts)
                
                discovered_companies.append(verified_company)

                # 4. Email Personalization for extracted contacts
                import asyncio
                from app.schemas.email_personalization import EmailPersonalizationRequest
                
                sem = asyncio.Semaphore(5)
                
                async def generate_draft(contact_dict: dict) -> bool:
                    if contact_dict["role_category"] not in ["hr", "recruiter", "talent_acquisition", "hiring_manager"]:
                        return False
                    
                    async with sem:
                        try:
                            template = "Hi {name},\n\nI noticed {company_name} is hiring in {location}. {company_insights}\n\nI have experience in this space: {portfolio_links}.\n\nBest,\n[Your Name]"
                            from uuid import UUID
                            email_req = EmailPersonalizationRequest(
                                template_content=template,
                                template_name="Automated Discovery Template",
                                contact_id=UUID(contact_dict["id"]),
                                company_intelligence_id=company_intel_id,
                                user_id=user_uuid,
                                save_draft=True,
                                run_in_background=False,
                                custom_instructions="Keep it concise and professional. Do not invent a resume link."
                            )
                            await email_pers_service.generate(email_req)
                            logger.info("Email drafted for contact", extra={"action": "email_drafted", "contact_id": contact_dict["id"]})
                            return True
                        except Exception as e:
                            logger.error(f"Failed to generate email for contact {contact_dict['id']}: {e}", extra={"action": "email_draft_failed", "error": str(e)})
                            return False

                draft_tasks = [generate_draft(c) for c in verified_company["verified_contacts"]]
                results = await asyncio.gather(*draft_tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, bool) and res:
                        emails_drafted += 1

        # 5. Phase 4: Result Aggregation and Ranking
        logger.info("Starting result aggregation and ranking", extra={"action": "aggregation_started"})
        # Sort companies by company_score (quality and completeness of contacts)
        discovered_companies.sort(key=lambda x: (x.get("company_score", 0), x.get("contacts_count", 0)), reverse=True)

        logger.info("Lead discovery task completed", extra={
            "action": "lead_discovery_completed",
            "contacts_discovered": total_contacts_discovered,
            "emails_drafted": emails_drafted,
            "processed_contact_ids": processed_contacts,
            "total_companies": len(discovered_companies)
        })
        
        metrics.emit_summary()

        # Clear active task if it is us
        from app.core.redis import get_redis_client
        redis = get_redis_client()
        active_task = await redis.get(f"active_discovery:{user_id}")
        active_task_str = active_task.decode() if isinstance(active_task, bytes) else active_task
        if active_task_str == request.context.run_id:
            await redis.delete(f"active_discovery:{user_id}")
            logger.info("Cleared active discovery task tracker", extra={"action": "tracker_cleared"})

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
