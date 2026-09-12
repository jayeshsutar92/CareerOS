import logging
import re
import asyncio
from urllib.parse import urlparse
from typing import Any

from app.ai.client import get_ai_client
from app.ai.models import AIRequest, AIMessage
from app.lead_discovery.search import JUNK_DOMAINS
from app.lead_discovery.models import CanonicalCompanyEntity, WebsiteCandidate, WebsiteCandidateSet, WebsiteResolutionEvidence
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

    @cached(prefix="website_resolution_phase3", ttl_seconds=86400 * 7, key_func=lambda self, entity, **kwargs: entity.normalized_name)
    async def resolve_website(self, entity: CanonicalCompanyEntity, metrics: DiscoveryMetrics | None = None) -> CanonicalCompanyEntity:
        search_query = f'"{entity.best_original_name}" official website company'
        
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
            logger.warning(f"DDG website search failed gracefully for {entity.normalized_name}: {e}")
            results = []

        candidate_set = WebsiteCandidateSet()
        
        # 1. Evaluate Search Engine Results
        for rank, r in enumerate(results):
            url = r.get("href", "")
            if not url: continue
            
            domain = self._normalize_domain(url)
            if not domain: continue
            
            if self._is_junk(domain):
                candidate_set.candidates.append(WebsiteCandidate(
                    domain=domain, url=url, score=0, source="DDG",
                    is_rejected=True, rejection_reason="Junk domain match"
                ))
                continue
                
            score = self._deterministic_score(domain, entity.best_original_name, rank)
            evidence = ["Search Match"]
            
            # Check title for company name match
            if entity.normalized_name in r.get("title", "").lower() or entity.normalized_name in r.get("body", "").lower():
                score += 15
                evidence.append("Name in Meta")
                
            candidate_set.candidates.append(WebsiteCandidate(
                domain=domain, url=url, score=score, source="DDG",
                evidence_signals=evidence
            ))
            
        # 2. Add candidates from Phase 1 Evidence (ATS, LinkedIn profiles sometimes have URLs)
        for ev in entity.evidence:
            domain = self._normalize_domain(ev.source_url)
            if not domain or self._is_junk(domain): continue
            
            score = self._deterministic_score(domain, entity.best_original_name, 5) # Default rank 5
            score += 10 # Bonus for being in discovery evidence
            candidate_set.candidates.append(WebsiteCandidate(
                domain=domain, url=ev.source_url, score=score, source=f"Evidence: {ev.provider}",
                evidence_signals=["Discovery Evidence"]
            ))

        ranked_candidates = candidate_set.get_ranked_valid_candidates()
        
        if not ranked_candidates:
            logger.info("No valid website candidates found", extra={"company": entity.normalized_name, "action": "website_resolution_failed"})
            entity.website_evidence = WebsiteResolutionEvidence(selected_url="", confidence=0, candidate_set=candidate_set)
            return entity

        top = ranked_candidates[0]
        ai_used = False
        
        # 3. AI Arbitration for Ties
        if len(ranked_candidates) > 1:
            runner_up = ranked_candidates[1]
            if top.score >= self.min_confidence and (top.score - runner_up.score) <= 10:
                logger.info("Website resolution ambiguous, invoking AI arbitration", extra={"company": entity.normalized_name, "top": top.domain, "runner_up": runner_up.domain})
                ai_used = True
                
                prompt = f"Which of these two domains is the official website for the company '{entity.best_original_name}'?\n"
                prompt += f"1. {top.url}\n"
                prompt += f"2. {runner_up.url}\n\n"
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
                    logger.info("AI resolution result", extra={"company": entity.normalized_name, "choice": choice})
                    
                    if "2" in choice:
                        top = runner_up
                        top.score += 20 # Boost score for AI selection
                        top.evidence_signals.append("AI Arbitrated Winner")
                    elif "0" in choice:
                        top.score -= 30 # Penalize
                        top.evidence_signals.append("AI Rejected")
                    else:
                        top.evidence_signals.append("AI Confirmed")
                except Exception as e:
                    logger.error(f"AI tie breaker failed: {e}")

        if top.score >= self.min_confidence:
            entity.website_evidence = WebsiteResolutionEvidence(
                selected_url=top.url,
                confidence=top.score,
                candidate_set=candidate_set,
                ai_arbitration_used=ai_used
            )
            
            logger.info("Resolved official website", extra={
                "company_name": entity.normalized_name,
                "resolved_url": top.url,
                "confidence": top.score,
                "action": "website_resolution_success",
                "ai_arbitration": ai_used
            })
        else:
            logger.info("Website resolution failed minimum confidence", extra={
                "company_name": entity.normalized_name,
                "best_url": top.url,
                "confidence": top.score,
                "action": "website_resolution_failed"
            })
            entity.website_evidence = WebsiteResolutionEvidence(selected_url="", confidence=0, candidate_set=candidate_set, ai_arbitration_used=ai_used)

        return entity
