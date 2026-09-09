import logging
import re
import asyncio
from urllib.parse import urlparse
from typing import Any

from app.ai.client import get_ai_client
from app.ai.models import AIRequest, AIMessage
from app.lead_discovery.search import CompanyLead, JUNK_DOMAINS
from duckduckgo_search import DDGS
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.cache import cached
from app.lead_discovery.metrics import DiscoveryMetrics

logger = logging.getLogger(__name__)

class WebsiteResolver:
    def __init__(self, min_confidence: int = 40):
        self.min_confidence = min_confidence
        self.ai_client = get_ai_client()

    def _normalize_domain(self, url: str) -> str:
        try:
            domain = urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    def _is_junk(self, domain: str) -> bool:
        for junk in JUNK_DOMAINS:
            if junk in domain:
                return True
        return False

    def _deterministic_score(self, domain: str, company_name: str, result_rank: int) -> int:
        score = 0
        name_clean = re.sub(r'[^\w]', '', company_name.lower())
        domain_clean = re.sub(r'\..*$', '', domain) # remove TLD

        # Exact match
        if name_clean and name_clean == domain_clean:
            score += 60
        # Partial match
        elif name_clean and (name_clean in domain_clean or domain_clean in name_clean):
            score += 30

        # TLD Preference
        if domain.endswith(".com"):
            score += 20
        elif domain.endswith((".co", ".io", ".net", ".org", ".co.in", ".in", ".ai")):
            score += 10

        # Rank bonus (higher ranks get slight boost)
        score += max(0, 5 - result_rank) * 2

        # Penalize extremely long domains relative to company name
        if len(domain_clean) > len(name_clean) * 2:
            score -= 15
            
        return score

    @cached(prefix="website_resolution", ttl_seconds=86400 * 7, key_func=lambda self, lead, **kwargs: lead.name.lower())
    async def resolve_website(self, lead: CompanyLead, metrics: DiscoveryMetrics | None = None) -> CompanyLead:
        search_query = f'"{lead.name}" official website company'
        
        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
        def do_search():
            with DDGS() as ddgs:
                return list(ddgs.text(search_query, max_results=8)) or []

        try:
            results = await asyncio.to_thread(do_search)
            if metrics:
                metrics.record_http_request(success=True)
        except Exception as e:
            if metrics:
                metrics.record_http_request(success=False)
            logger.warning(f"DDG website search failed gracefully for {lead.name}: {e}")
            return lead

        candidates = {}
        for rank, r in enumerate(results):
            url = r.get("href", "")
            if not url: continue
            
            domain = self._normalize_domain(url)
            if not domain or self._is_junk(domain):
                logger.debug("Rejected junk domain", extra={"company_name": lead.name, "rejected_domain": domain})
                continue
                
            if domain not in candidates:
                score = self._deterministic_score(domain, lead.name, rank)
                candidates[domain] = {"url": url, "score": score, "title": r.get("title", ""), "body": r.get("body", ""), "rank": rank}

        if not candidates:
            logger.info("No valid website candidates found", extra={"company": lead.name, "action": "website_resolution_failed"})
            lead.resolution_evidence["website_rejection_reason"] = "No valid non-junk candidates"
            return lead

        # Sort by score descending
        sorted_cands = sorted(candidates.values(), key=lambda x: x["score"], reverse=True)
        top = sorted_cands[0]
        
        # AI Tie breaking logic
        if len(sorted_cands) > 1:
            runner_up = sorted_cands[1]
            if top["score"] >= self.min_confidence and (top["score"] - runner_up["score"]) < 15:
                logger.info("Website resolution ambiguous, invoking AI", extra={"company": lead.name, "top": top["url"], "runner_up": runner_up["url"]})
                
                prompt = f"Which of these two domains is the official website for the company '{lead.name}'?\n"
                prompt += f"1. {top['url']} - {top['title']}\n{top['body']}\n\n"
                prompt += f"2. {runner_up['url']} - {runner_up['title']}\n{runner_up['body']}\n\n"
                prompt += "Reply with exactly '1', '2', or '0' if neither is correct."
                
                req = AIRequest(
                    messages=[
                        AIMessage(role="system", content="You are a data entry assistant helping to identify official websites. Output only the digit 1, 2, or 0. No other text."),
                        AIMessage(role="user", content=prompt)
                    ],
                    temperature=0.0
                )
                
                try:
                    if metrics:
                        metrics.record_ai_invocation()
                    resp = await asyncio.wait_for(self.ai_client.complete(req), timeout=10.0)
                    choice = resp.choices[0].message.content.strip()
                    logger.info("AI resolution result", extra={"company": lead.name, "choice": choice})
                    
                    if "2" in choice:
                        top = runner_up
                        top["score"] += 20 # Boost score for AI selection
                        lead.resolution_evidence["website_ai_adj"] = "runner_up_selected"
                    elif "0" in choice:
                        top["score"] -= 30 # Penalize
                        lead.resolution_evidence["website_ai_adj"] = "both_rejected"
                    else:
                        lead.resolution_evidence["website_ai_adj"] = "top_confirmed"
                except Exception as e:
                    logger.error(f"AI tie breaker failed: {e}")

        if top["score"] >= self.min_confidence:
            lead.url = top["url"]
            lead.is_official_resolved = True
            lead.website_confidence = top["score"]
            lead.resolution_evidence["website_candidates"] = [c["url"] for c in sorted_cands[:3]]
            
            logger.info("Resolved official website", extra={
                "company_name": lead.name,
                "resolved_url": lead.url,
                "confidence": lead.website_confidence,
                "action": "website_resolution_success"
            })
        else:
            logger.info("Website resolution failed minimum confidence", extra={
                "company_name": lead.name,
                "best_url": top["url"],
                "best_score": top["score"],
                "action": "website_resolution_rejected_low_confidence"
            })
            lead.resolution_evidence["website_rejection_reason"] = f"Low confidence: {top['score']} < {self.min_confidence}"
            
        return lead
