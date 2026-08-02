from __future__ import annotations

import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.contact_discovery.normalizer import classify_role, normalize_whitespace
from app.schemas.contact import ContactCandidate, ContactMethod

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
        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "CareerOS contact discovery"})
            response.raise_for_status()
            return response.text


class PublicContactExtractor:
    def extract(self, html: str, *, source_url: str, company_name: str) -> list[ContactCandidate]:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        shared_methods = self._extract_contact_methods(html, source_url)
        candidates = self._extract_from_text(
            soup.get_text("\n"),
            source_url=source_url,
            company_name=company_name,
        )

        for candidate in candidates:
            candidate.contact_methods = self._merge_methods(
                candidate.contact_methods, shared_methods
            )

        return self._dedupe_candidates(candidates)

    def _extract_from_text(
        self,
        text: str,
        *,
        source_url: str,
        company_name: str,
    ) -> list[ContactCandidate]:
        candidates: list[ContactCandidate] = []
        for line in text.splitlines():
            line = normalize_whitespace(line)
            if not ROLE_RE.search(line):
                continue
            for match in NAME_ROLE_RE.finditer(line):
                role = normalize_whitespace(match.group("role"))
                if classify_role(role) == "other":
                    continue
                candidates.append(
                    ContactCandidate(
                        name=normalize_whitespace(match.group("name")),
                        role=role,
                        company_name=company_name,
                        contact_methods=[ContactMethod(type="source_page", value=source_url)],
                        source_url=source_url,
                    )
                )
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
