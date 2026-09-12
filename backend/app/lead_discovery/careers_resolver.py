import logging
import asyncio
import re
from urllib.parse import urljoin, urlparse
from typing import Any

from app.lead_discovery.models import CanonicalCompanyEntity, CareersSurfaceCandidate, CareersSurfaceSet, SocialResolutionEvidence
from app.company_intelligence.extractor import CompanyWebsiteFetcher
from app.lead_discovery.metrics import DiscoveryMetrics
from app.core.cache import cached

logger = logging.getLogger(__name__)

ATS_DOMAINS = [
    "greenhouse.io", "boards.greenhouse.io", "jobs.lever.co", "lever.co",
    "workdayjobs.com", "myworkdayjobs.com", "ashbyhq.com", "jobs.ashbyhq.com",
    "smartrecruiters.com", "bamboohr.com", "bamboohr.co.uk", "rippling-ats.com",
    "recruitee.com", "teamtailor.com", "careers.teamtailor.com"
]

class CareersResolver:
    def __init__(self):
        self.fetcher = CompanyWebsiteFetcher(timeout_seconds=10.0)

    def _normalize_url(self, url: str) -> str:
        """Strip trailing slash and fragments for deduplication."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        
    def _is_ats_url(self, url: str) -> bool:
        domain = urlparse(url).netloc.lower()
        return any(ats in domain for ats in ATS_DOMAINS)

    @cached(prefix="careers_resolution_phase6", ttl_seconds=86400 * 7, key_func=lambda self, entity, *args, **kwargs: entity.canonical_id)
    async def resolve_careers(self, entity: CanonicalCompanyEntity, evidence_coll_dict: dict[str, Any], social_evidence: SocialResolutionEvidence, metrics: DiscoveryMetrics | None = None) -> CareersSurfaceSet:
        logger.info("Starting careers surface discovery", extra={"company_name": entity.normalized_name, "canonical_id": entity.canonical_id})
        
        surface_set = CareersSurfaceSet(canonical_id=entity.canonical_id)
        seen_urls = set()
        
        def add_candidate(url: str, surface_type: str, method: str, priority: int, source: str, depth: int, signals: list[str]):
            if not url: return
            norm_url = self._normalize_url(url)
            if norm_url in seen_urls:
                return
            seen_urls.add(norm_url)
            
            # Reclassify if it's actually an ATS
            if self._is_ats_url(url):
                surface_type = "ats_portal"
                
            candidate = CareersSurfaceCandidate(
                url=url,
                surface_type=surface_type,
                discovery_method=method,
                discovery_priority=priority,
                source_url=source,
                crawl_depth=depth,
                evidence_signals=signals
            )
            surface_set.candidates.append(candidate)
            
        # 1. ATS URLs and Career Pages from Evidence Collection
        if evidence_coll_dict and "evidence" in evidence_coll_dict:
            for ev in evidence_coll_dict["evidence"]:
                if ev["evidence_type"] == "ats_link":
                    add_candidate(ev["value"], "ats_portal", "Phase4_Evidence", 1, ev["source_urls"][0] if ev.get("source_urls") else "", 0, ["Found in earlier discovery phase"])
                elif ev["evidence_type"] == "careers_page":
                    add_candidate(ev["value"], "internal_careers_page", "Phase4_Evidence", 4, ev["source_urls"][0] if ev.get("source_urls") else "", 0, ["Extracted from official website HTML"])
                    
        # 2. Check sitemap.xml and robots.txt
        if entity.website_evidence and entity.website_evidence.selected_url:
            base_url = entity.website_evidence.selected_url
            robots_url = urljoin(base_url, "/robots.txt")
            sitemap_url = urljoin(base_url, "/sitemap.xml")
            
            # Fetch robots.txt
            try:
                if metrics: metrics.record_http_request(success=True)
                robots_txt, _ = await self.fetcher.fetch_page(robots_url)
                for line in robots_txt.splitlines():
                    if "sitemap:" in line.lower():
                        sm_match = re.search(r"sitemap:\s*(http[^\s]+)", line, re.I)
                        if sm_match:
                            add_candidate(sm_match.group(1), "sitemap", "robots.txt", 3, robots_url, 1, ["Found via robots.txt"])
            except Exception:
                if metrics: metrics.record_http_request(success=False)
                
            # Fetch sitemap.xml
            try:
                if metrics: metrics.record_http_request(success=True)
                sitemap_xml, _ = await self.fetcher.fetch_page(sitemap_url)
                # Naive regex for urls containing career/job
                career_urls = set(re.findall(r"<loc>(http[^<]+(?:career|job|lever|greenhouse|workday|ashby)[^<]*)</loc>", sitemap_xml, re.I))
                for cu in career_urls:
                    add_candidate(cu, "sitemap_discovery", "sitemap.xml", 2, sitemap_url, 1, ["Found via sitemap.xml regex match"])
            except Exception:
                if metrics: metrics.record_http_request(success=False)
                
        logger.info("Careers discovery finished", extra={
            "company_name": entity.normalized_name,
            "surface_count": len(surface_set.candidates)
        })
        
        return surface_set
