from typing import Protocol

from duckduckgo_search import DDGS

class JobSearchProvider(Protocol):
    async def search_companies(self, location: str, work_mode: str) -> list[str]:
        ...

class DuckDuckGoJobSearchProvider:
    def __init__(self, max_results: int = 5):
        self.max_results = max_results
        
    async def search_companies(self, location: str, work_mode: str) -> list[str]:
        query = f'"{work_mode}" jobs in "{location}" software engineering hiring OR careers -site:linkedin.com/jobs -site:glassdoor.com'
        results = DDGS().text(query, max_results=self.max_results)
        
        # We just extract the base titles or company names if possible, but actually DDG returns snippets
        # Let's extract URLs to search for contacts
        urls = [r["href"] for r in results if "href" in r]
        
        return urls

class AISearchProvider:
    def __init__(self, max_results: int = 5):
        self.max_results = max_results

    async def search_companies(self, location: str, work_mode: str) -> list[str]:
        import json
        from app.ai.client import get_ai_client
        from app.ai.models import AIMessage, AIRequest

        prompt = (
            f"You are a recruitment assistant. Find {self.max_results} real companies hiring for software engineering roles "
            f"that are {work_mode} and located in or hiring from {location}. "
            "Return ONLY a JSON array of their main website URLs. Do not include careers page URLs, just the main domain (e.g. https://www.example.com). "
            "IMPORTANT: Prioritize very small startups or agencies. Do NOT return large companies like Amazon, Swiggy, Flipkart, Upwork, Google, etc. "
            "Make sure the companies exist."
        )
        
        request = AIRequest(
            messages=[
                AIMessage(role="system", content="Output valid JSON array of strings only. No markdown formatting like ```json."),
                AIMessage(role="user", content=prompt)
            ],
            temperature=0.7
        )
        
        try:
            client = get_ai_client()
            response = await client.complete(request)
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            
            # The AI might output ```json \n [ ... ] \n ```
            if content.startswith("json"):
                content = content[4:].strip()
                
            return json.loads(content)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"AISearchProvider failed: {e}")
            return []

def get_job_search_provider() -> JobSearchProvider:
    return AISearchProvider(max_results=3)

