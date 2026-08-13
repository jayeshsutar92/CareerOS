from typing import Protocol

from duckduckgo_search import DDGS

class JobSearchProvider(Protocol):
    async def search_companies(self, location: str, work_mode: str) -> list[str]:
        ...

import urllib.parse
import httpx
from bs4 import BeautifulSoup
import logging

import httpx
import logging
import urllib.parse
import re

class RealJobSearchProvider:
    def __init__(self, max_results: int = 5):
        self.max_results = max_results
        
    async def search_companies(self, location: str, work_mode: str) -> list[str]:
        # Target real job APIs: Jobicy and Remotive
        urls = []
        seen_companies = set()
        
        async with httpx.AsyncClient() as client:
            try:
                # 1. Jobicy API
                # Fetch remote jobs. Jobicy is mainly remote, so we use it if remote is preferred or as fallback.
                jobicy_url = "https://jobicy.com/api/v2/remote-jobs?industry=engineering"
                res = await client.get(jobicy_url, timeout=10.0)
                if res.status_code == 200:
                    data = res.json()
                    for job in data.get("jobs", []):
                        company_name = job.get("companyName", "")
                        job_geo = job.get("jobGeo", "").lower()
                        
                        # Apply location filtering if needed
                        if location.lower() != "remote" and location.lower() not in job_geo and "anywhere" not in job_geo:
                            continue
                            
                        if company_name:
                            clean_name = re.sub(r'[^a-zA-Z0-9]', '', company_name).lower()
                            if clean_name and clean_name not in seen_companies:
                                seen_companies.add(clean_name)
                                urls.append(f"https://www.{clean_name}.com")
                                if len(urls) >= self.max_results:
                                    return urls
            except Exception as e:
                logging.getLogger(__name__).error(f"Jobicy API failed: {e}")

            try:
                # 2. Remotive API
                remotive_url = f"https://remotive.com/api/remote-jobs?category=software-dev&limit={self.max_results * 3}"
                # If location is provided, we can pass search param
                if location and location.lower() != "remote":
                    remotive_url += f"&search={urllib.parse.quote(location)}"
                    
                res = await client.get(remotive_url, timeout=10.0)
                if res.status_code == 200:
                    data = res.json()
                    for job in data.get("jobs", []):
                        company_name = job.get("company_name", "")
                        if company_name:
                            clean_name = re.sub(r'[^a-zA-Z0-9]', '', company_name).lower()
                            if clean_name and clean_name not in seen_companies:
                                seen_companies.add(clean_name)
                                urls.append(f"https://www.{clean_name}.com")
                                if len(urls) >= self.max_results:
                                    return urls
            except Exception as e:
                logging.getLogger(__name__).error(f"Remotive API failed: {e}")

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
    return RealJobSearchProvider(max_results=5)

