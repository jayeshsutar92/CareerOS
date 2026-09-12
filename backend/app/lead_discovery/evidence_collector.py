import logging
import asyncio
from typing import Any

from app.lead_discovery.models import CanonicalCompanyEntity, EvidenceCollection
from app.company_intelligence.extractor import CompanyWebsiteFetcher, CompanyIntelligenceExtractor
from app.lead_discovery.metrics import DiscoveryMetrics
from app.core.cache import cached

logger = logging.getLogger(__name__)

class EvidenceCollector:
    def __init__(self):
        self.fetcher = CompanyWebsiteFetcher(timeout_seconds=10.0)
        self.extractor = CompanyIntelligenceExtractor()
        
    @cached(prefix="evidence_collection", ttl_seconds=86400 * 7, key_func=lambda self, entity, **kwargs: entity.canonical_id)
    async def collect(self, entity: CanonicalCompanyEntity, metrics: DiscoveryMetrics | None = None) -> dict[str, Any]:
        """
        Collects deterministic evidence for a canonical company entity.
        Returns a serialized dict of EvidenceCollection to allow caching.
        """
        logger.info("Starting evidence collection", extra={"company_name": entity.normalized_name, "canonical_id": entity.canonical_id})
        
        collection = EvidenceCollection(canonical_id=entity.canonical_id)
        
        # 1. Collect from Phase 1 Discovery Evidence (e.g. ATS URLs)
        for ev in entity.evidence:
            collection.add_evidence(
                ev_type="discovery_evidence_url",
                value=ev.source_url,
                source_url=ev.source_url,
                method=f"phase_1_provider:{ev.provider}"
            )
            if "ats" in ev.provider.lower():
                collection.add_evidence(
                    ev_type="ats_link",
                    value=ev.source_url,
                    source_url=ev.source_url,
                    method="phase_1_provider"
                )
                
        # 2. Collect from Official Website (if resolved)
        if entity.website_evidence and entity.website_evidence.selected_url:
            official_url = entity.website_evidence.selected_url
            try:
                if metrics:
                    metrics.record_http_request(success=True)
                html, headers = await self.fetcher.fetch_page(official_url)
                
                # Use deterministic extractor
                extracted_data = self.extractor.extract(html=html, base_url=official_url, headers=headers)
                
                # Map extracted structured data into ExtractedEvidence format
                if "contact_info" in extracted_data:
                    contact_info = extracted_data["contact_info"]
                    
                    for email in contact_info.get("emails", []):
                        collection.add_evidence("email", email, official_url, "html_regex_extractor")
                        
                    for phone in contact_info.get("phones", []):
                        collection.add_evidence("phone", phone, official_url, "html_regex_extractor")
                        
                    for social, link in contact_info.get("socials", {}).items():
                        collection.add_evidence(f"social_profile_{social}", link, official_url, "html_regex_extractor")
                        
                if extracted_data.get("about_url"):
                    collection.add_evidence("about_page", extracted_data["about_url"], official_url, "html_link_discovery")
                    
                if extracted_data.get("careers_url"):
                    collection.add_evidence("careers_page", extracted_data["careers_url"], official_url, "html_link_discovery")
                    
                if extracted_data.get("tech_stack"):
                    for tech in extracted_data["tech_stack"]:
                        collection.add_evidence("tech_signature", tech, official_url, "header_html_signature_match")
                        
            except Exception as e:
                if metrics:
                    metrics.record_http_request(success=False)
                logger.warning("Failed to fetch official website for evidence collection", extra={
                    "company_name": entity.normalized_name,
                    "url": official_url,
                    "error": str(e)
                })
        
        logger.info("Evidence collection finished", extra={
            "company_name": entity.normalized_name,
            "evidence_count": len(collection.evidence)
        })
        
        # We return a dict representation to safely store it in Redis via @cached
        return {
            "canonical_id": collection.canonical_id,
            "evidence": [
                {
                    "evidence_type": e.evidence_type,
                    "value": e.value,
                    "source_urls": e.source_urls,
                    "methods": e.methods,
                    "first_seen": e.first_seen
                } for e in collection.evidence
            ]
        }
