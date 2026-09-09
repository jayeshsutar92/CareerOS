import logging
import re
from typing import Protocol, Any
import asyncio
from dataclasses import dataclass, field
from urllib.parse import urlparse

from duckduckgo_search import DDGS
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

JUNK_DOMAINS = {
    "wikipedia.org", "linkedin.com", "naukri.com", "glassdoor.", "indeed.",
    "ambitionbox.com", "crunchbase.com", "bloomberg.com", "pitchbook.com",
    "zaubacorp.com", "justdial.com", "vcsdata.com", "topcompanieslist.com",
    "f6s.com", "zoominfo.com", "dnb.com", "yelp.com", "yellowpages.com",
    "facebook.com", "twitter.com", "x.com", "instagram.com", "youtube.com",
    "glassdoor.co.in", "indeed.co.in"
}

@dataclass
class CompanyLead:
    name: str
    url: str
    source_score: int
    source_name: str
    is_official_resolved: bool = False
    website_confidence: int = 0
    socials: dict[str, str] = field(default_factory=dict)
    resolution_evidence: dict[str, Any] = field(default_factory=dict)

class BaseSearchProvider(Protocol):
    async def search_companies(self, job_role: str | None, location: str, work_mode: str, max_results: int) -> list[CompanyLead]:
        ...

class DDGSearchProvider:
    """Base class for DuckDuckGo based search providers."""
    def __init__(self):
        pass
        
    async def _safe_search(self, query: str, max_results: int) -> list[dict[str, Any]]:
        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
        def do_search():
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return results or []
            
        try:
            return await asyncio.to_thread(do_search)
        except Exception as e:
            logger.error(f"DDG search failed for query '{query}': {e}")
            return []

class ATSDirectoryProvider(DDGSearchProvider):
    async def search_companies(self, job_role: str | None, location: str, work_mode: str, max_results: int) -> list[CompanyLead]:
        job_str = f"{job_role} " if job_role else ""
        search_query = f"\"{job_str.strip()}\" {location} {work_mode} site:jobs.lever.co OR site:boards.greenhouse.io OR site:apply.workable.com"
        logger.info("Querying ATS Directory Provider", extra={"query": search_query})
        
        results = await self._safe_search(search_query, max_results=max_results + 10)
        
        leads = []
        for r in results:
            url = r.get("href", "")
            title = r.get("title", "")
            if not url or not any(x in url.lower() for x in ["lever.co", "greenhouse.io", "workable.com"]):
                continue
            
            # Extract company name from ATS URL (e.g. jobs.lever.co/companyname)
            domain_parts = urlparse(url).path.strip("/").split("/")
            if not domain_parts:
                continue
                
            name_slug = domain_parts[0]
            name = name_slug.replace("-", " ").title()
            
            # Clean title
            clean_title = re.sub(r'[^a-zA-Z0-9\s-]', '', title).split("-")[0].strip()
            if clean_title and len(clean_title) < 40 and len(clean_title) > 2:
                name = clean_title
                
            leads.append(CompanyLead(name=name, url=url, source_score=90, source_name="Google/DDG: ATS", is_official_resolved=False))
            if len(leads) >= max_results:
                break
        
        logger.info("ATS Directory Provider finished", extra={"found": len(leads)})
        return leads

class LinkedInCompanyProvider(DDGSearchProvider):
    async def search_companies(self, job_role: str | None, location: str, work_mode: str, max_results: int) -> list[CompanyLead]:
        job_str = f"{job_role} " if job_role else ""
        search_query = f"site:linkedin.com/company {job_str}{location}"
        logger.info("Querying LinkedIn Company Provider", extra={"query": search_query})
        
        results = await self._safe_search(search_query, max_results=max_results + 5)
        
        leads = []
        for r in results:
            url = r.get("href", "")
            title = r.get("title", "")
            if not url or "linkedin.com/company" not in url: continue
            
            # LinkedIn title is usually "Company Name | LinkedIn" or "Company Name - Overview"
            name = title.split("|")[0].strip()
            name = re.split(r'\s*-\s*Overview|\s*-\s*Home|\s*\|\s*LinkedIn', name, flags=re.IGNORECASE)[0].strip()
            
            leads.append(CompanyLead(name=name, url=url, source_score=60, source_name="Google/DDG: LinkedIn", is_official_resolved=False))
            if len(leads) >= max_results:
                break
                
        logger.info("LinkedIn Company Provider finished", extra={"found": len(leads)})
        return leads

class NaukriProvider(DDGSearchProvider):
    async def search_companies(self, job_role: str | None, location: str, work_mode: str, max_results: int) -> list[CompanyLead]:
        job_str = f"{job_role} " if job_role else ""
        search_query = f"site:naukri.com/job-listings {job_str}{location}"
        logger.info("Querying Naukri Provider", extra={"query": search_query})
        
        results = await self._safe_search(search_query, max_results=max_results + 5)
        
        leads = []
        for r in results:
            url = r.get("href", "")
            title = r.get("title", "")
            if not url or "naukri.com" not in url: continue
            
            # Naukri title: "Careers in CompanyName - Jobs in CompanyName"
            name = title.split("|")[0].strip()
            name = re.sub(r'(?i)Careers\s+in\s+', '', name)
            name = re.sub(r'(?i)\s*-\s*Jobs\s+in\s+.*$', '', name)
            name = re.split(r'\s*-\s*Naukri\.com', name, flags=re.IGNORECASE)[0].strip()
            
            leads.append(CompanyLead(name=name, url=url, source_score=40, source_name="Google/DDG: Naukri", is_official_resolved=False))
            if len(leads) >= max_results:
                break
                
        logger.info("Naukri Provider finished", extra={"found": len(leads)})
        return leads

class SearchPipeline:
    def __init__(self, max_results: int = 10):
        self.max_results = max_results
        self.providers: list[BaseSearchProvider] = [
            ATSDirectoryProvider(),
            LinkedInCompanyProvider(),
            NaukriProvider(),
        ]
        self.ddg_provider = DDGSearchProvider()
        # Semaphore to limit concurrent DDG official resolution searches
        self._resolution_semaphore = asyncio.Semaphore(3)
        
    # _resolve_official_website has been moved to WebsiteResolver
        
    async def search_companies(self, job_role: str | None, location: str, work_mode: str, batch_size: int | None = None, metrics: Any = None) -> list[CompanyLead]:
        limit = batch_size if batch_size is not None else self.max_results
        logger.info("Starting company search pipeline", extra={"job_role": job_role, "location": location, "work_mode": work_mode, "batch_size": limit})
        
        # Run all providers concurrently
        tasks = [p.search_companies(job_role, location, work_mode, limit) for p in self.providers]
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_leads: list[CompanyLead] = []
        for res in results_lists:
            if isinstance(res, list):
                all_leads.extend(res)
            elif isinstance(res, Exception):
                logger.error(f"Search provider failed: {res}")
                
        # Phase 1: Entity Resolution (Normalize, Score, Deduplicate BEFORE Website Resolution)
        from app.lead_discovery.entity_resolver import EntityResolver
        resolver = EntityResolver(min_confidence=40)
        resolved_entities = resolver.resolve_entities(all_leads, location)
        
        # Take more than `limit` into Website Resolution to account for junk domain drops
        top_entities = resolved_entities[:limit * 2]
        
        # Phase 2: Resolve official websites concurrently for the canonical entities
        from app.lead_discovery.website_resolver import WebsiteResolver
        from app.lead_discovery.social_resolver import SocialResolver
        
        web_resolver = WebsiteResolver(min_confidence=40)
        soc_resolver = SocialResolver(min_confidence=40)
        
        resolve_tasks = [web_resolver.resolve_website(lead, metrics=metrics) for lead in top_entities]
        resolved_leads = await asyncio.gather(*resolve_tasks, return_exceptions=True)
        
        valid_leads = [l for l in resolved_leads if isinstance(l, CompanyLead) and l.is_official_resolved]
        
        # Phase 2b: Resolve social profiles for valid leads
        social_tasks = [soc_resolver.resolve_socials(lead, metrics=metrics) for lead in valid_leads]
        final_valid_leads = await asyncio.gather(*social_tasks, return_exceptions=True)
        valid_leads = [l for l in final_valid_leads if isinstance(l, CompanyLead)]
        
        final_leads = valid_leads[:limit]
        
        for lead in final_leads:
            logger.info("Selected company for discovery", extra={
                "company_name": lead.name,
                "provider_used": lead.source_name,
                "resolved_official_domain": lead.url if lead.is_official_resolved else None,
                "socials_resolved": list(lead.socials.keys()),
                "raw_url": lead.url,
                "ranking_reason": f"Score {lead.source_score} (Deduplicated Entity)",
                "action": "company_selected"
            })
            
        logger.info("Pipeline finished", extra={
            "total_discovered": len(all_leads), 
            "entities_resolved": len(resolved_entities),
            "websites_resolved": len([l for l in valid_leads if l.is_official_resolved]),
            "returned": len(final_leads)
        })
        return final_leads

def get_job_search_provider() -> SearchPipeline:
    return SearchPipeline()
