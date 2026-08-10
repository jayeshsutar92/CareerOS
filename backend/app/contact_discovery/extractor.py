from __future__ import annotations

import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

import json

from app.ai.client import get_ai_client
from app.ai.models import AIMessage, AIRequest
from app.contact_discovery.normalizer import classify_role, normalize_whitespace
from app.schemas.contact import ContactCandidate, ContactMethod

GENERIC_EMAIL_RE = re.compile(
    r"^(info|sales|careers|hello|contact|support|hr|jobs|admin|press|marketing|team)@", re.I
)

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3})?[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})")
LINKEDIN_RE = re.compile(r"https?://(?:[\w]+\.)?linkedin\.com/in/[\w\-/%]+", re.I)
ROLE_RE = re.compile(
    r"\b(HR|Human Resources|People Operations|People Partner|Recruiter|Technical Recruiter|"
    r"Talent Acquisition|Sourcer|Hiring Manager|Engineering Manager|Engineering Lead|"
    r"Head of Engineering)\b",
    re.I,
)
NAME_ROLE_RE = re.compile(
    r"(?P<name>[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*"
    r"(?:[-|,]|\s+is\s+)?\s*"
    r"(?P<role>(?:Senior\s+|Lead\s+|Principal\s+)?(?:HR|Human Resources|People Operations|"
    r"People Partner|Recruiter|Technical Recruiter|Talent Acquisition|Sourcer|Hiring Manager|"
    r"Engineering Manager|Engineering Lead|Head of Engineering))",
    re.I,
)


class PublicContactFetcher:
    def __init__(self, timeout_seconds: float = 15.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def fetch(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True, verify=False) as client:
            response = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
            response.raise_for_status()
            return response.text


class PublicContactExtractor:
    async def extract(self, html: str, *, source_url: str, company_name: str) -> list[ContactCandidate]:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        shared_methods = self._extract_contact_methods(html, source_url)
        candidates = await self._extract_from_text(
            soup.get_text("\n"),
            source_url=source_url,
            company_name=company_name,
        )

        filtered_methods = []
        for method in shared_methods:
            if method.type == "email" and GENERIC_EMAIL_RE.match(method.value):
                continue
            filtered_methods.append(method)

        candidates = await self._map_methods_to_candidates(candidates, filtered_methods)

        return self._dedupe_candidates(candidates)

    async def _map_methods_to_candidates(
        self, candidates: list[ContactCandidate], methods: list[ContactMethod]
    ) -> list[ContactCandidate]:
        if not candidates or not methods:
            return candidates

        if len(candidates) == 1:
            candidates[0].contact_methods = self._merge_methods(
                candidates[0].contact_methods, methods
            )
            return candidates

        try:
            client = get_ai_client()
            
            c_list = [{"id": i, "name": c.name, "role": c.role} for i, c in enumerate(candidates)]
            m_list = [{"id": i, "type": m.type, "value": m.value} for i, m in enumerate(methods)]
            
            prompt = (
                "You are an expert HR data extractor. Given a list of people and a list of contact methods (emails, linkedin, etc) found on a single page, "
                "map the correct contact methods to the corresponding person based on standard naming conventions (e.g. j.smith@company.com belongs to John Smith).\n"
                "Rules:\n"
                "1. ONLY output JSON in this format: { \"mappings\": [ { \"candidate_id\": <int>, \"method_ids\": [<int>, <int>] } ] }\n"
                "2. DO NOT fabricate or guess any emails not in the list.\n"
                "3. If an email/linkedin clearly belongs to a specific person, map it. Otherwise, leave it unmapped.\n"
            )
            
            user_msg = f"People:\n{json.dumps(c_list)}\n\nMethods:\n{json.dumps(m_list)}"
            
            request = AIRequest(
                messages=[
                    AIMessage(role="system", content=prompt),
                    AIMessage(role="user", content=user_msg)
                ],
                temperature=0.0
            )
            response = await client.complete(request)
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            
            data = json.loads(content)
            mappings = {item.get("candidate_id"): item.get("method_ids", []) for item in data.get("mappings", [])}
            
            for i, candidate in enumerate(candidates):
                matched_method_ids = mappings.get(i, [])
                matched_methods = [methods[m_id] for m_id in matched_method_ids if m_id < len(methods)]
                candidate.contact_methods = self._merge_methods(candidate.contact_methods, matched_methods)
                
        except Exception:
            pass

        return candidates

    async def _extract_from_text(
        self,
        text: str,
        *,
        source_url: str,
        company_name: str,
    ) -> list[ContactCandidate]:
        candidates: list[ContactCandidate] = []
        
        # Limit text to ~20k characters to prevent huge token costs
        cleaned_text = text[:20000]
        
        prompt = (
            f"You are a recruitment assistant. Analyze the text below from a company website ({company_name}) "
            "and find all HR, recruiters, talent acquisition, and hiring managers mentioned. "
            "Only return a JSON array containing objects with 'name' and 'role'. "
            "If none are found, return an empty array [].\n\n"
            f"Text content:\n{cleaned_text}"
        )
        
        try:
            client = get_ai_client()
            request = AIRequest(
                messages=[
                    AIMessage(role="system", content="Output valid JSON array of objects only. No markdown formatting like ```json. Example: [{\"name\": \"John\", \"role\": \"HR\"}]"),
                    AIMessage(role="user", content=prompt)
                ],
                temperature=0.0
            )
            response = await client.complete(request)
            content = response.content.strip()
            
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            
            if content.startswith("json"):
                content = content[4:].strip()
                
            data = json.loads(content)
            
            for item in data:
                if "name" in item and "role" in item:
                    role = normalize_whitespace(item["role"])
                    if classify_role(role) == "other":
                        continue
                    candidates.append(
                        ContactCandidate(
                            name=normalize_whitespace(item["name"]),
                            role=role,
                            company_name=company_name,
                            contact_methods=[ContactMethod(type="source_page", value=source_url)],
                            source_url=source_url,
                        )
                    )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"AI candidate extraction failed: {e}")
            
        return candidates

    def _extract_contact_methods(self, html: str, source_url: str) -> list[ContactMethod]:
        methods: list[ContactMethod] = []
        soup = BeautifulSoup(html, "html.parser")

        for email in EMAIL_RE.findall(html):
            methods.append(ContactMethod(type="email", value=email))

        for phone in PHONE_RE.findall(html):
            methods.append(ContactMethod(type="phone", value=phone))

        for linkedin_url in LINKEDIN_RE.findall(html):
            methods.append(ContactMethod(type="linkedin", value=linkedin_url.rstrip("/")))

        for anchor in soup.find_all("a", href=True):
            href = str(anchor["href"])
            if href.startswith("mailto:"):
                email = href.removeprefix("mailto:").split("?")[0]
                if email:
                    methods.append(ContactMethod(type="email", value=email))
            elif "linkedin.com/in/" in href:
                methods.append(
                    ContactMethod(type="linkedin", value=urljoin(source_url, href).rstrip("/"))
                )

        methods.append(ContactMethod(type="source_page", value=source_url))
        return self._merge_methods([], methods)

    def _merge_methods(
        self,
        current: list[ContactMethod],
        extra: list[ContactMethod],
    ) -> list[ContactMethod]:
        merged: dict[tuple[str, str], ContactMethod] = {}
        for method in [*current, *extra]:
            merged[(method.type, method.value.lower())] = method
        return list(merged.values())

    def _dedupe_candidates(self, candidates: list[ContactCandidate]) -> list[ContactCandidate]:
        seen: set[tuple[str, str, str]] = set()
        deduped: list[ContactCandidate] = []
        for candidate in candidates:
            key = (candidate.company_name.lower(), candidate.name.lower(), candidate.role.lower())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(candidate)
        return deduped
