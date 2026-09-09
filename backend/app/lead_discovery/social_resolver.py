import logging
import asyncio
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from app.company_intelligence.extractor import (
    CompanyWebsiteFetcher,
    LINKEDIN_RE,
    TWITTER_RE,
    GITHUB_RE,
)
from app.lead_discovery.search import CompanyLead
from duckduckgo_search import DDGS

from app.ai.client import get_ai_client
from app.ai.models import AIRequest, AIMessage
from app.core.cache import cached
from app.lead_discovery.metrics import DiscoveryMetrics

logger = logging.getLogger(__name__)

FACEBOOK_RE = re.compile(r"https?://(?:[\w]+\.)?facebook\.com/[\w\-/%]+", re.I)
INSTAGRAM_RE = re.compile(r"https?://(?:[\w]+\.)?instagram\.com/[\w\-/%]+", re.I)
YOUTUBE_RE = re.compile(r"https?://(?:[\w]+\.)?youtube\.com/(?:c/|channel/|user/|@)?[\w\-/%]+", re.I)

class SocialResolver:
    def __init__(self, min_confidence: int = 40):
        self.min_confidence = min_confidence
        self.fetcher = CompanyWebsiteFetcher(timeout_seconds=10.0)
        self.ai_client = get_ai_client()

    def _extract_from_html(self, html: str) -> dict[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        socials = {}
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "linkedin" not in socials and LINKEDIN_RE.search(href):
                socials["linkedin"] = href
            elif "twitter" not in socials and TWITTER_RE.search(href):
                socials["twitter"] = href
            elif "github" not in socials and GITHUB_RE.search(href):
                socials["github"] = href
            elif "facebook" not in socials and FACEBOOK_RE.search(href):
                socials["facebook"] = href
            elif "instagram" not in socials and INSTAGRAM_RE.search(href):
                socials["instagram"] = href
            elif "youtube" not in socials and YOUTUBE_RE.search(href):
                socials["youtube"] = href
        return socials

    def _deterministic_score(self, url: str, company_name: str, platform: str) -> int:
        score = 0
        path = urlparse(url).path.lower()
        name_clean = re.sub(r'[^\w]', '', company_name.lower())
        
        # Avoid generic paths like /home, /share, /jobs
        if re.search(r'/(?:home|share|login|signup|post|intent|sharer|jobs)', path):
            return 0
            
        if name_clean and name_clean in path:
            score += 60
        else:
            score += 20
            
        return score

    async def _fallback_search(self, company_name: str, platform: str, metrics: DiscoveryMetrics | None = None) -> str | None:
        query = f'"{company_name}" official {platform} page company'
        
        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
        def do_search():
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=5)) or []

        try:
            results = await asyncio.to_thread(do_search)
            if metrics:
                metrics.record_http_request(success=True)
        except Exception as e:
            if metrics:
                metrics.record_http_request(success=False)
            logger.warning(f"DDG fallback social search failed gracefully for {platform}: {e}")
            return None

        candidates = {}
        for r in results:
            url = r.get("href", "")
            if not url or platform.lower() not in url.lower(): continue
            
            score = self._deterministic_score(url, company_name, platform)
            if score > 0:
                candidates[url] = {"url": url, "score": score, "title": r.get("title", ""), "body": r.get("body", "")}
                
        if not candidates:
            return None
            
        sorted_cands = sorted(candidates.values(), key=lambda x: x["score"], reverse=True)
        top = sorted_cands[0]
        
        # AI Tie breaker logic
        if len(sorted_cands) > 1:
            runner_up = sorted_cands[1]
            if top["score"] >= self.min_confidence and (top["score"] - runner_up["score"]) < 20:
                logger.info(f"Social resolution ambiguous for {platform}, invoking AI", extra={"company": company_name})
                
                prompt = f"Which of these two {platform} profiles is the official one for '{company_name}'?\n"
                prompt += f"1. {top['url']} - {top['title']}\n{top['body']}\n\n"
                prompt += f"2. {runner_up['url']} - {runner_up['title']}\n{runner_up['body']}\n\n"
                prompt += "Reply with exactly '1', '2', or '0' if neither is correct."
                
                req = AIRequest(messages=[AIMessage(role="user", content=prompt)], max_output_tokens=5, temperature=0.0)
                try:
                    resp = await self.ai_client.complete(req)
                    choice = resp.choices[0].message.content.strip()
                    logger.info("AI resolution result for social", extra={"company": company_name, "choice": choice})
                    if "2" in choice:
                        top = runner_up
                    elif "0" in choice:
                        top["score"] = 0
                except Exception as e:
                    logger.error(f"AI tie breaker failed for social: {e}")
                    
        if top["score"] >= self.min_confidence:
            return top["url"]
        return None

    @cached(prefix="social_resolution", ttl_seconds=86400 * 7, key_func=lambda self, lead, **kwargs: lead.url)
    async def resolve_socials(self, lead: CompanyLead, metrics: DiscoveryMetrics | None = None) -> CompanyLead:
        if not lead.is_official_resolved or not lead.url:
            return lead

        extracted_socials = {}
        # 1. Fetch official website to extract socials natively
        try:
            html, _ = await self.fetcher.fetch_page(lead.url)
            extracted_socials = self._extract_from_html(html)
            logger.info("Extracted social profiles directly from website", extra={
                "company_name": lead.name,
                "found_platforms": list(extracted_socials.keys()),
                "action": "social_extraction_success"
            })
            lead.resolution_evidence["socials_from_html"] = list(extracted_socials.keys())
        except Exception as e:
            logger.warning(f"Failed to fetch {lead.url} for social extraction: {e}")
            lead.resolution_evidence["social_html_error"] = str(e)
            
        for platform, url in extracted_socials.items():
            lead.socials[platform] = url
            
        # 2. Fallback search for missing critical platforms
        critical_platforms = ["linkedin", "twitter"]
        for platform in critical_platforms:
            if platform not in lead.socials:
                url = await self._fallback_search(lead.name, platform, metrics)
                if url:
                    lead.socials[platform] = url
                    logger.info(f"Resolved {platform} via fallback search", extra={"company_name": lead.name, "url": url, "action": "social_fallback_success"})
                    if "social_fallback" not in lead.resolution_evidence:
                        lead.resolution_evidence["social_fallback"] = []
                    lead.resolution_evidence["social_fallback"].append(platform)
                else:
                    logger.info(f"Fallback search yielded no valid candidates for {platform}", extra={"company_name": lead.name})

        return lead
