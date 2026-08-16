import logging
import re
import asyncio
from typing import Protocol, Any
from duckduckgo_search import DDGS
from tenacity import retry, stop_after_attempt, wait_exponential

from app.schemas.contact import ContactCandidate, ContactMethod
from app.contact_discovery.extractor import PublicContactExtractor, PublicContactFetcher
from app.contact_discovery.normalizer import classify_role, normalize_whitespace

logger = logging.getLogger(__name__)

class BaseContactExtractorProvider(Protocol):
    async def extract_contacts(self, company_name: str, source_urls: list[str]) -> list[ContactCandidate]:
        ...

class WebsiteExtractorProvider:
    def __init__(self):
        self.fetcher = PublicContactFetcher()
        self.extractor = PublicContactExtractor()
        
    async def extract_contacts(self, company_name: str, source_urls: list[str]) -> list[ContactCandidate]:
        all_candidates = []
        for source_url in source_urls:
            base_url = str(source_url).rstrip('/')
            paths = ["", "/about", "/about-us", "/team", "/careers"]
            
            async def fetch_path(p):
                try:
                    return await self.fetcher.fetch(base_url + p)
                except Exception:
                    return ""
            
            # Fetch pages concurrently
            htmls = await asyncio.gather(*[fetch_path(p) for p in paths])
            combined_html = "\\n".join([h for h in htmls if h])
            
            if not combined_html:
                continue

            candidates = await self.extractor.extract(
                combined_html,
                source_url=str(source_url),
                company_name=company_name,
            )
            logger.info("Source analyzed", extra={"action": "source_analyzed", "source": source_url, "candidates_found": len(candidates)})
            all_candidates.extend(candidates)
            
        return all_candidates

class LinkedInSearchExtractorProvider:
    def __init__(self):
        pass
        
    async def _safe_search(self, query: str, max_results: int) -> list[dict[str, Any]]:
        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
        def do_search():
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                return results or []
        
        return await asyncio.to_thread(do_search)
        
    async def extract_contacts(self, company_name: str, source_urls: list[str]) -> list[ContactCandidate]:
        candidates = []
        # We query duckduckgo for linkedin profiles related to the company
        query = f'site:linkedin.com/in "{company_name}" ("HR" OR "Recruiter" OR "Engineering Manager" OR "Talent Acquisition" OR "People Operations")'
        
        try:
            results = await self._safe_search(query, max_results=10)
        except Exception as e:
            logger.error(f"LinkedIn snippet search failed for {company_name}: {e}")
            return []
            
        for r in results:
            url = r.get("href", "")
            title = r.get("title", "")
            snippet = r.get("body", "")
            
            if not url or "linkedin.com/in/" not in url:
                continue
                
            # Title usually format: "John Doe - Senior Recruiter - Company Name | LinkedIn"
            # Try to parse name and role from title
            parts = [p.strip() for p in title.split("-")]
            name = parts[0]
            role = ""
            
            if len(parts) > 1:
                role = parts[1]
                # Sometimes it's "John Doe - Company Name" if role is missing in title
                # We can fallback to snippet parsing if role seems like a company name
                if company_name.lower() in role.lower() and len(parts) > 2:
                    role = parts[2]
            
            # Strip "| LinkedIn" from name or role
            name = name.split("|")[0].strip()
            role = role.split("|")[0].strip()
            
            # Basic validation
            if len(name.split()) > 4 or len(name) < 3:
                continue
                
            role_category = classify_role(role)
            if role_category == "other":
                # Try to find a role in snippet
                match = re.search(r'(HR|Human Resources|People Operations|Recruiter|Talent Acquisition|Hiring Manager|Engineering Manager)', snippet, re.IGNORECASE)
                if match:
                    role = match.group(1)
                else:
                    continue
                    
            candidates.append(ContactCandidate(
                name=normalize_whitespace(name),
                role=normalize_whitespace(role),
                company_name=company_name,
                source_url=url, # Use their linkedin as source
                contact_methods=[
                    ContactMethod(type="linkedin", value=url.rstrip('/')),
                    ContactMethod(type="source_page", value="Google/DDG: LinkedIn Snippet")
                ]
            ))
            
        logger.info("Source analyzed", extra={"action": "source_analyzed", "source": "LinkedIn Search", "candidates_found": len(candidates)})
        return candidates

class ContactExtractionPipeline:
    def __init__(self):
        self.providers: list[BaseContactExtractorProvider] = [
            WebsiteExtractorProvider(),
            LinkedInSearchExtractorProvider(),
        ]
        
    async def extract_contacts(self, company_name: str, source_urls: list[str]) -> list[ContactCandidate]:
        tasks = [p.extract_contacts(company_name, source_urls) for p in self.providers]
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_candidates = []
        for res in results_lists:
            if isinstance(res, list):
                all_candidates.extend(res)
            elif isinstance(res, Exception):
                logger.error(f"Contact extraction provider failed: {res}")
                
        # Deduplication happens later in ContactService.upsert_candidate but we can do basic dedupe here
        return all_candidates
