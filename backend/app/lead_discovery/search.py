import logging
import re
from typing import Protocol, Any
import asyncio
from dataclasses import dataclass
from urllib.parse import urlparse

from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

@dataclass
class CompanyLead:
    name: str
    url: str
    source_score: int
    source_name: str

class BaseSearchProvider(Protocol):
    async def search_companies(self, location: str, query: str, max_results: int) -> list[CompanyLead]:
        ...

class DDGSearchProvider:
    """Base class for DuckDuckGo based search providers."""
    def __init__(self):
        pass
        
    async def _safe_search(self, query: str, max_results: int) -> list[dict[str, Any]]:
        from tenacity import retry, stop_after_attempt, wait_exponential
        
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
    async def search_companies(self, location: str, query: str, max_results: int) -> list[CompanyLead]:
        search_query = f"{query} companies in {location} official site"
        results = await self._safe_search(search_query, max_results=max_results + 5)
        
        leads = []
        for r in results:
            url = r.get("href", "")
            title = r.get("title", "")
            if not url or "linkedin.com" in url or "naukri.com" in url or "glassdoor.com" in url: 
                continue
            
            # Simple domain extraction
            domain = urlparse(url).netloc.replace("www.", "")
            name = domain.split(".")[0].capitalize()
            # Try to get a better name from title
            clean_title = re.sub(r'[^a-zA-Z0-9\s-]', '', title).split("-")[0].strip()
            if clean_title and len(clean_title) < 30:
                name = clean_title
                
            leads.append(CompanyLead(name=name, url=url, source_score=100, source_name="Google/DDG: Official Site"))
            if len(leads) >= max_results:
                break
        return leads

class LinkedInCompanyProvider(DDGSearchProvider):
    async def search_companies(self, location: str, query: str, max_results: int) -> list[CompanyLead]:
        search_query = f"site:linkedin.com/company {query} {location}"
        results = await self._safe_search(search_query, max_results=max_results + 5)
        
        leads = []
        for r in results:
            url = r.get("href", "")
            title = r.get("title", "")
            if not url or "linkedin.com/company" not in url: continue
            
            # Title is usually "Company Name | LinkedIn"
            name = title.split("|")[0].strip()
            name = re.sub(r'\s*[-\|].*$', '', name) # Strip suffix
            leads.append(CompanyLead(name=name, url=url, source_score=90, source_name="Google/DDG: LinkedIn"))
            if len(leads) >= max_results:
                break
        return leads

class NaukriProvider(DDGSearchProvider):
    async def search_companies(self, location: str, query: str, max_results: int) -> list[CompanyLead]:
        search_query = f"site:naukri.com/job-listings {query} {location}"
        results = await self._safe_search(search_query, max_results=max_results + 5)
        
        leads = []
        for r in results:
            url = r.get("href", "")
            title = r.get("title", "")
            if not url or "naukri.com" not in url: continue
            
            name = title.split("|")[0].strip()
            name = re.sub(r'\s*[-\|].*$', '', name) # Strip suffix
            leads.append(CompanyLead(name=name, url=url, source_score=70, source_name="Google/DDG: Naukri"))
            if len(leads) >= max_results:
                break
        return leads

class SearchPipeline:
    def __init__(self, max_results: int = 10):
        self.max_results = max_results
        self.providers: list[BaseSearchProvider] = [
            OfficialWebsiteProvider(),
            LinkedInCompanyProvider(),
            NaukriProvider(),
        ]
        
    async def search_companies(self, location: str, query: str) -> list[CompanyLead]:
        # Run all providers concurrently
        tasks = [p.search_companies(location, query, self.max_results) for p in self.providers]
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_leads = []
        for res in results_lists:
            if isinstance(res, list):
                all_leads.extend(res)
            elif isinstance(res, Exception):
                logger.error(f"Search provider failed: {res}")
                
        # Deduplicate and sort by score
        seen_names = set()
        deduped_leads = []
        
        # Sort by score first so we keep the highest scored version of a duplicate
        all_leads.sort(key=lambda x: x.source_score, reverse=True)
        
        for lead in all_leads:
            clean_name = re.sub(r'[^a-zA-Z0-9]', '', lead.name).lower()
            if clean_name not in seen_names and clean_name:
                seen_names.add(clean_name)
                deduped_leads.append(lead)
                
        return deduped_leads[:self.max_results]

def get_job_search_provider() -> SearchPipeline:
    return SearchPipeline(max_results=5)
