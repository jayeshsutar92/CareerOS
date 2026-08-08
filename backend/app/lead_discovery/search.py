from typing import Protocol

from duckduckgo_search import DDGS

class JobSearchProvider(Protocol):
    def search_companies(self, location: str, work_mode: str) -> list[str]:
        ...

class DuckDuckGoJobSearchProvider:
    def __init__(self, max_results: int = 5):
        self.max_results = max_results
        
    def search_companies(self, location: str, work_mode: str) -> list[str]:
        query = f'"{work_mode}" jobs in "{location}" software engineering hiring OR careers -site:linkedin.com/jobs -site:glassdoor.com'
        results = DDGS().text(query, max_results=self.max_results)
        
        # We just extract the base titles or company names if possible, but actually DDG returns snippets
        # Let's extract URLs to search for contacts
        urls = [r["href"] for r in results if "href" in r]
        
        return urls

class AISearchProvider:
    # We could also just ask the AI to guess 3 companies hiring in that region
    # But duckduckgo is better for live web sources.
    pass

def get_job_search_provider() -> JobSearchProvider:
    return DuckDuckGoJobSearchProvider(max_results=3)

