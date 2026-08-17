import logging
import re
from typing import Protocol, Any
import asyncio
from dataclasses import dataclass
from urllib.parse import urlparse

from duckduckgo_search import DDGS
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

@dataclass
class CompanyLead:
    name: str
    url: str
    source_score: int
    source_name: str
    is_official_resolved: bool = False

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

class OfficialWebsiteProvider(DDGSearchProvider):
    async def search_companies(self, job_role: str | None, location: str, work_mode: str, max_results: int) -> list[CompanyLead]:
        job_str = f"{job_role} " if job_role else "companies "
        search_query = f"{job_str}{work_mode} jobs in {location} company careers -site:linkedin.com -site:naukri.com -site:glassdoor.com -site:indeed.com"
        logger.info("Querying Official Website Provider", extra={"query": search_query})
        
        results = await self._safe_search(search_query, max_results=max_results + 10)
        
        leads = []
        for r in results:
            url = r.get("href", "")
            title = r.get("title", "")
            if not url or any(x in url.lower() for x in ["linkedin.com", "naukri.com", "glassdoor.com", "indeed.com"]): 
                continue
            
            # Simple domain extraction
            domain = urlparse(url).netloc.replace("www.", "")
            name = domain.split(".")[0].capitalize()
            # Try to get a better name from title
            clean_title = re.sub(r'[^a-zA-Z0-9\s-]', '', title).split("-")[0].strip()
            if clean_title and len(clean_title) < 30:
                name = clean_title
                
            leads.append(CompanyLead(name=name, url=url, source_score=100, source_name="Google/DDG: Official Site", is_official_resolved=True))
            if len(leads) >= max_results:
                break
        
        logger.info("Official Website Provider finished", extra={"found": len(leads)})
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
            
            # Title is usually "Company Name | LinkedIn"
            name = title.split("|")[0].strip()
            name = re.sub(r'\s*[-\|].*$', '', name) # Strip suffix
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
            
            name = title.split("|")[0].strip()
            name = re.sub(r'\s*[-\|].*$', '', name) # Strip suffix
            leads.append(CompanyLead(name=name, url=url, source_score=40, source_name="Google/DDG: Naukri", is_official_resolved=False))
            if len(leads) >= max_results:
                break
                
        logger.info("Naukri Provider finished", extra={"found": len(leads)})
        return leads

class SearchPipeline:
    def __init__(self, max_results: int = 10):
        self.max_results = max_results
        self.providers: list[BaseSearchProvider] = [
            OfficialWebsiteProvider(),
            LinkedInCompanyProvider(),
            NaukriProvider(),
        ]
        self.ddg_provider = DDGSearchProvider()
        # Semaphore to limit concurrent DDG official resolution searches
        self._resolution_semaphore = asyncio.Semaphore(3)
        
    async def _resolve_official_website(self, lead: CompanyLead) -> CompanyLead:
        """Resolve aggregator/directory URL to an official website."""
        if lead.is_official_resolved:
            return lead
            
        search_query = f"{lead.name} official website -site:linkedin.com -site:naukri.com -site:glassdoor.com -site:indeed.com -site:ambitionbox.com"
        
        async with self._resolution_semaphore:
            results = await self.ddg_provider._safe_search(search_query, max_results=3)
            
        for r in results:
            url = r.get("href", "")
            if not url: continue
            if any(x in url.lower() for x in ["linkedin.com", "naukri.com", "glassdoor.com", "indeed.com", "ambitionbox.com", "wikipedia.org"]):
                continue
            
            logger.info("Resolved official website", extra={
                "company_name": lead.name,
                "original_url": lead.url,
                "resolved_url": url,
                "provider": lead.source_name,
                "action": "resolve_official_website_success"
            })
            lead.url = url
            lead.is_official_resolved = True
            return lead
            
        logger.info("Failed to resolve official website", extra={
            "company_name": lead.name,
            "original_url": lead.url,
            "action": "resolve_official_website_failed"
        })
        return lead
        
    async def search_companies(self, job_role: str | None, location: str, work_mode: str, batch_size: int | None = None) -> list[CompanyLead]:
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
                
        # Resolve official websites concurrently for those that need it
        resolve_tasks = [self._resolve_official_website(lead) for lead in all_leads]
        resolved_leads = await asyncio.gather(*resolve_tasks, return_exceptions=True)
        
        valid_leads = [l for l in resolved_leads if isinstance(l, CompanyLead)]
        
        # Deduplicate by normalized domain and sort by score
        def normalize_domain(url: str) -> str:
            try:
                # If we couldn't resolve, just use the raw URL to avoid deduplicating all aggregators together
                if any(x in url.lower() for x in ["linkedin.com", "naukri.com", "glassdoor.com", "indeed.com"]):
                    return url.lower()
                domain = urlparse(url).netloc.lower()
                if domain.startswith("www."):
                    domain = domain[4:]
                return domain
            except Exception:
                return ""
                
        seen_domains = set()
        deduped_leads = []
        
        # Sort by score first so we keep the highest scored version of a duplicate
        valid_leads.sort(key=lambda x: x.source_score, reverse=True)
        
        for lead in valid_leads:
            domain = normalize_domain(lead.url)
            if domain and domain not in seen_domains:
                seen_domains.add(domain)
                deduped_leads.append(lead)
                
        final_leads = deduped_leads[:limit]
        
        for lead in final_leads:
            logger.info("Selected company for discovery", extra={
                "company_name": lead.name,
                "provider_used": lead.source_name,
                "resolved_official_domain": lead.url if lead.is_official_resolved else None,
                "raw_url": lead.url,
                "ranking_reason": f"Score {lead.source_score} (Deduplicated)",
                "action": "company_selected"
            })
            
        logger.info("Pipeline finished", extra={
            "total_discovered": len(all_leads), 
            "deduplicated": len(deduped_leads), 
            "returned": len(final_leads)
        })
        return final_leads

def get_job_search_provider() -> SearchPipeline:
    return SearchPipeline()
