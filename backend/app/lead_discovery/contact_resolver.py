import logging
import asyncio
import re
from typing import Any

from app.lead_discovery.models import (
    CanonicalCompanyEntity,
    SocialResolutionEvidence,
    CareersSurfaceSet,
    ContactCandidateSet,
    ContactDiscoveryEvidence,
    PersonCandidate,
    CommunicationChannelCandidate
)
from app.contact_discovery.extractor import PublicContactFetcher, PublicContactExtractor, EMAIL_RE, ROLE_RE
from app.contact_discovery.normalizer import classify_role
from app.lead_discovery.metrics import DiscoveryMetrics
from app.core.cache import cached

logger = logging.getLogger(__name__)

GENERIC_HIRING_EMAILS_RE = re.compile(r"^(careers|jobs|hr|talent|recruiting|hiring|work)@", re.I)

class ContactResolver:
    def __init__(self):
        self.fetcher = PublicContactFetcher(timeout_seconds=15.0)
        self.extractor = PublicContactExtractor()

    def _merge_people(self, candidate_set: ContactCandidateSet, new_person: PersonCandidate):
        # Deterministic deduplication
        for p in candidate_set.people:
            # Match by email
            if new_person.email and p.email and new_person.email.lower() == p.email.lower():
                self._merge_person_evidence(p, new_person)
                return
            # Match by LinkedIn
            if new_person.linkedin_url and p.linkedin_url and new_person.linkedin_url.lower() == p.linkedin_url.lower():
                self._merge_person_evidence(p, new_person)
                return
            # Match by normalized name and role
            if new_person.name and p.name and new_person.name.lower() == p.name.lower() and new_person.role_classification == p.role_classification:
                self._merge_person_evidence(p, new_person)
                return
        
        candidate_set.people.append(new_person)
        
    def _merge_person_evidence(self, existing: PersonCandidate, new_person: PersonCandidate):
        existing.source_urls.extend([u for u in new_person.source_urls if u not in existing.source_urls])
        existing.evidence_signals.extend([s for s in new_person.evidence_signals if s not in existing.evidence_signals])
        if not existing.email and new_person.email: existing.email = new_person.email
        if not existing.linkedin_url and new_person.linkedin_url: existing.linkedin_url = new_person.linkedin_url
        if not existing.job_title and new_person.job_title: existing.job_title = new_person.job_title

    def _merge_channels(self, candidate_set: ContactCandidateSet, new_channel: CommunicationChannelCandidate):
        for c in candidate_set.channels:
            if c.channel_type == new_channel.channel_type and c.value.lower() == new_channel.value.lower():
                c.source_urls.extend([u for u in new_channel.source_urls if u not in c.source_urls])
                c.evidence_signals.extend([s for s in new_channel.evidence_signals if s not in c.evidence_signals])
                return
        candidate_set.channels.append(new_channel)

    @cached(prefix="contact_resolution_phase7", ttl_seconds=86400 * 7, key_func=lambda self, entity, *args, **kwargs: entity.canonical_id)
    async def resolve_contacts(self, 
        entity: CanonicalCompanyEntity, 
        evidence_coll_dict: dict[str, Any], 
        social_evidence: SocialResolutionEvidence, 
        careers_surfaces: CareersSurfaceSet, 
        metrics: DiscoveryMetrics | None = None
    ) -> ContactDiscoveryEvidence:
        logger.info("Starting contact discovery", extra={"company_name": entity.normalized_name, "canonical_id": entity.canonical_id})
        
        evidence = ContactDiscoveryEvidence(canonical_id=entity.canonical_id)
        candidate_set = evidence.candidate_set
        
        # Priority Queue of URLs to scrape
        urls_to_scrape = []
        
        # 1. ATS Portals and Careers pages
        for surface in careers_surfaces.candidates:
            if not surface.is_rejected:
                urls_to_scrape.append((surface.url, surface.surface_type))
                
        # 2. LinkedIn Company Page (from Social Resolution)
        if "linkedin" in social_evidence.resolved_profiles:
            urls_to_scrape.append((social_evidence.resolved_profiles["linkedin"], "linkedin_company_page"))

        # Deduplicate URLs to scrape
        seen_scrape_urls = set()
        unique_urls_to_scrape = []
        for url, stype in urls_to_scrape:
            if url not in seen_scrape_urls:
                seen_scrape_urls.add(url)
                unique_urls_to_scrape.append((url, stype))

        # We will parse explicitly pre-collected emails first
        if evidence_coll_dict and "evidence" in evidence_coll_dict:
            for ev in evidence_coll_dict["evidence"]:
                if ev["evidence_type"] == "email":
                    email = ev["value"]
                    if GENERIC_HIRING_EMAILS_RE.match(email):
                        self._merge_channels(candidate_set, CommunicationChannelCandidate(
                            channel_type="email",
                            value=email,
                            discovery_source="EvidenceCollection",
                            source_urls=ev.get("source_urls", []),
                            discovery_method="Phase4_Evidence",
                            evidence_signals=["Discovered on official website as generic hiring email"]
                        ))

        # Scrape and extract
        for url, surface_type in unique_urls_to_scrape[:3]: # Limit to top 3 to save time and AI calls
            try:
                if metrics: metrics.record_http_request(success=True)
                html = await self.fetcher.fetch(url)
                if not html:
                    continue
                    
                # Deterministic Regex extraction for emails on these specific hiring pages
                emails = set(EMAIL_RE.findall(html))
                for email in emails:
                    if GENERIC_HIRING_EMAILS_RE.match(email):
                        self._merge_channels(candidate_set, CommunicationChannelCandidate(
                            channel_type="email",
                            value=email,
                            discovery_source=surface_type,
                            source_urls=[url],
                            discovery_method="regex_extraction",
                            evidence_signals=[f"Found on {surface_type}"]
                        ))

                # Use GPT Extraction for complex person parsing ONLY on these verified surfaces
                extracted_candidates = await self.extractor.extract(html, source_url=url, company_name=entity.best_original_name)
                
                for cand in extracted_candidates:
                    if not cand.email and not cand.linkedin_url and not cand.name:
                        continue # Skip empty fabrications
                        
                    person = PersonCandidate(
                        name=cand.name,
                        job_title=cand.role,
                        department="Human Resources", # Default inference
                        role_classification=cand.role_category,
                        email=cand.email,
                        linkedin_url=cand.linkedin_url,
                        discovery_source=surface_type,
                        source_urls=[url],
                        discovery_method="ai_extraction",
                        evidence_signals=[cand.evidence]
                    )
                    self._merge_people(candidate_set, person)
                    
            except Exception as e:
                if metrics: metrics.record_http_request(success=False)
                logger.warning(f"Contact extraction failed for {url}: {e}")

        logger.info("Contact discovery finished", extra={
            "company_name": entity.normalized_name,
            "people_count": len(candidate_set.people),
            "channels_count": len(candidate_set.channels)
        })
        
        return evidence
