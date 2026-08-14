from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

import json

from app.ai.client import get_ai_client
from app.ai.models import AIMessage, AIRequest
from app.contact_discovery.normalizer import classify_role, normalize_whitespace
from app.schemas.contact import ContactCandidate, ContactMethod

logger = logging.getLogger(__name__)

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
            try:
                response = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
                if response.status_code == 404:
                    logger.info(f"Skipping 404 URL: {url}", extra={"action": "fetch_url_404", "url": url})
                    return ""
                response.raise_for_status()
                return response.text
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP {e.response.status_code} for URL: {url}", extra={"action": "fetch_url_http_error", "url": url, "status": e.response.status_code})
                return ""
            except Exception as e:
                logger.warning(f"Failed to fetch {url}: {e}", extra={"action": "fetch_url_error", "url": url})
                return ""


def _clean_text(raw_text: str) -> str:
    """Collapse excessive whitespace/blank lines so the AI prompt is compact and useful."""
    # Replace runs of whitespace-only lines with a single newline
    cleaned = re.sub(r"\n\s*\n", "\n", raw_text)
    # Collapse multiple spaces/tabs within lines
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in cleaned.split("\n")]
    # Drop empty lines and very short noise lines (< 2 chars)
    lines = [line for line in lines if len(line) >= 2]
    return "\n".join(lines)


class PublicContactExtractor:
    async def extract(self, html: str, *, source_url: str, company_name: str) -> list[ContactCandidate]:
        import urllib.parse
        import asyncio
        import dns.resolver
        import smtplib
        import random
        import string
        from app.schemas.contact import ContactCandidate, ContactMethod

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        raw_text = soup.get_text("\n")
        cleaned_text = _clean_text(raw_text)

        logger.info(
            "Text extracted from HTML for AI analysis",
            extra={
                "action": "text_extracted",
                "source_url": source_url,
                "company_name": company_name,
                "raw_text_length": len(raw_text),
                "cleaned_text_length": len(cleaned_text),
                "html_length": len(html),
            },
        )

        shared_methods = self._extract_contact_methods(html, source_url)

        # --- Step 1: AI-based extraction ---
        candidates = await self._extract_from_text(
            cleaned_text,
            source_url=source_url,
            company_name=company_name,
        )
        logger.info(
            "AI extraction completed",
            extra={
                "action": "ai_extraction_result",
                "source_url": source_url,
                "ai_candidates_count": len(candidates),
            },
        )

        # --- Step 2: Regex-based fallback if AI returned nothing ---
        if not candidates:
            regex_candidates = self._extract_from_regex(
                cleaned_text,
                source_url=source_url,
                company_name=company_name,
            )
            if regex_candidates:
                logger.info(
                    "Regex fallback produced candidates (AI returned empty)",
                    extra={
                        "action": "regex_fallback_result",
                        "source_url": source_url,
                        "regex_candidates_count": len(regex_candidates),
                    },
                )
                candidates = regex_candidates

        # --- Step 3: Structured HTML extraction fallback ---
        if not candidates:
            html_candidates = self._extract_from_html_structure(
                soup,
                source_url=source_url,
                company_name=company_name,
            )
            if html_candidates:
                logger.info(
                    "HTML structure fallback produced candidates",
                    extra={
                        "action": "html_structure_fallback_result",
                        "source_url": source_url,
                        "html_candidates_count": len(html_candidates),
                    },
                )
                candidates = html_candidates

        if not candidates:
            logger.warning(
                "All extraction methods returned zero candidates",
                extra={
                    "action": "extraction_empty",
                    "source_url": source_url,
                    "company_name": company_name,
                    "cleaned_text_length": len(cleaned_text),
                    "cleaned_text_preview": cleaned_text[:500],
                },
            )

        filtered_methods = []
        for method in shared_methods:
            if method.type == "email" and GENERIC_EMAIL_RE.match(method.value):
                continue
            filtered_methods.append(method)

        candidates = await self._map_methods_to_candidates(candidates, filtered_methods)

        # SMTP VERIFICATION WORKFLOW
        domain = urllib.parse.urlparse(source_url).netloc.replace("www.", "")
        
        def _verify_email(email: str) -> bool:
            try:
                records = dns.resolver.resolve(domain, 'MX')
                mx_record = str(records[0].exchange)
                server = smtplib.SMTP(timeout=5)
                server.set_debuglevel(0)
                server.connect(mx_record)
                server.helo(server.local_hostname)
                server.mail("hello@example.com")
                code, _ = server.rcpt(email)
                server.quit()
                return code == 250
            except Exception:
                return False

        random_prefix = ''.join(random.choices(string.ascii_lowercase, k=10))
        is_catch_all = await asyncio.to_thread(_verify_email, f"{random_prefix}@{domain}")

        verified_candidates = []

        if not is_catch_all:
            # 1. Verify specific extracted candidates by generating standard permutations
            for c in candidates:
                has_email = any(m.type == 'email' for m in c.contact_methods)
                if not has_email and " " in c.name:
                    parts = c.name.lower().split(" ")
                    first = parts[0]
                    last = "".join(parts[1:])
                    perms = [
                        f"{first}@{domain}",
                        f"{first}.{last}@{domain}",
                        f"{first[0]}{last}@{domain}",
                        f"{first}_{last}@{domain}"
                    ]
                    for perm in perms:
                        valid = await asyncio.to_thread(_verify_email, perm)
                        if valid:
                            c.contact_methods.append(ContactMethod(type="email", value=perm))
                            break

            # 2. Fallback: discover generic department contacts if needed
            generic_roles = [
                ("HR", f"hr@{domain}"),
                ("Talent Acquisition", f"talent@{domain}"),
                ("Recruiter", f"careers@{domain}"),
                ("Recruiter", f"recruiting@{domain}")
            ]
            async def verify_generic(role_name, email):
                if await asyncio.to_thread(_verify_email, email):
                    return ContactCandidate(
                        name=f"{company_name} {role_name}",
                        role=role_name,
                        company_name=company_name,
                        source_url=source_url,
                        contact_methods=[ContactMethod(type="email", value=email)]
                    )
                return None

            tasks = [verify_generic(rn, em) for rn, em in generic_roles]
            results = await asyncio.gather(*tasks)
            verified_candidates.extend([r for r in results if r])

        all_candidates = candidates + verified_candidates
        logger.info(
            "Extraction pipeline completed",
            extra={
                "action": "extraction_complete",
                "source_url": source_url,
                "total_candidates": len(all_candidates),
                "from_extraction": len(candidates),
                "from_smtp_verification": len(verified_candidates),
            },
        )
        return self._dedupe_candidates(all_candidates)

    def _extract_from_regex(
        self,
        text: str,
        *,
        source_url: str,
        company_name: str,
    ) -> list[ContactCandidate]:
        """Fallback: use regex patterns to find Name-Role pairs in the text."""
        candidates: list[ContactCandidate] = []
        seen: set[tuple[str, str]] = set()

        for match in NAME_ROLE_RE.finditer(text):
            name = normalize_whitespace(match.group("name"))
            role = normalize_whitespace(match.group("role"))
            role_category = classify_role(role)
            if role_category == "other":
                continue
            key = (name.lower(), role.lower())
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                ContactCandidate(
                    name=name,
                    role=role,
                    company_name=company_name,
                    contact_methods=[ContactMethod(type="source_page", value=source_url)],
                    source_url=source_url,
                )
            )

        if candidates:
            logger.info(
                "Regex extraction found candidates",
                extra={
                    "action": "regex_extraction",
                    "source_url": source_url,
                    "count": len(candidates),
                    "names": [c.name for c in candidates],
                },
            )
        return candidates

    def _extract_from_html_structure(
        self,
        soup: BeautifulSoup,
        *,
        source_url: str,
        company_name: str,
    ) -> list[ContactCandidate]:
        """Fallback: look for team member cards/sections in HTML structure."""
        candidates: list[ContactCandidate] = []
        seen: set[tuple[str, str]] = set()

        # Look for common team page patterns: cards with a heading + role text
        # Search for elements that contain role keywords in their text
        role_elements = soup.find_all(
            string=ROLE_RE,
        )

        for role_el in role_elements:
            role_text = normalize_whitespace(role_el.strip())
            role_category = classify_role(role_text)
            if role_category == "other":
                continue

            # Walk up to find the parent container (card/div)
            parent = role_el.parent
            for _ in range(5):  # Walk up at most 5 levels
                if parent is None:
                    break
                parent_text = parent.get_text(" ", strip=True)
                # Look for a name pattern in this container
                # A name is typically 2-4 capitalized words
                name_match = re.search(
                    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
                    parent_text,
                )
                if name_match:
                    name = normalize_whitespace(name_match.group(1))
                    # Skip if the "name" is actually a generic phrase
                    if name.lower() in ("our team", "about us", "meet our", "the team"):
                        parent = parent.parent
                        continue
                    key = (name.lower(), role_text.lower())
                    if key not in seen:
                        seen.add(key)
                        candidates.append(
                            ContactCandidate(
                                name=name,
                                role=role_text,
                                company_name=company_name,
                                contact_methods=[ContactMethod(type="source_page", value=source_url)],
                                source_url=source_url,
                            )
                        )
                    break
                parent = parent.parent

        if candidates:
            logger.info(
                "HTML structure extraction found candidates",
                extra={
                    "action": "html_structure_extraction",
                    "source_url": source_url,
                    "count": len(candidates),
                    "names": [c.name for c in candidates],
                },
            )
        return candidates

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
        
        text_length = len(cleaned_text)
        if text_length < 50:
            logger.warning(
                "Text too short for AI extraction, skipping",
                extra={
                    "action": "ai_extraction_skipped_short_text",
                    "source_url": source_url,
                    "text_length": text_length,
                    "text_preview": cleaned_text[:200],
                },
            )
            return candidates

        prompt = (
            f"You are a recruitment assistant. Analyze the text below from a company website ({company_name}) "
            "and extract ALL people who work in HR, recruiting, talent acquisition, people operations, or engineering management.\n\n"
            "Look for:\n"
            "- Names near titles like HR, Human Resources, Recruiter, Technical Recruiter, "
            "Talent Acquisition, Hiring Manager, Engineering Manager, People Operations, Head of Engineering\n"
            "- Names in team/about sections even if the role title is not directly adjacent\n"
            "- Names mentioned alongside hiring, recruiting, or HR-related context\n\n"
            "Return a JSON array of objects with 'name' (full name) and 'role' (their job title or function).\n"
            "If you find people but are unsure of their exact title, use the closest matching role from the text.\n"
            "If genuinely no relevant people are mentioned, return an empty array [].\n\n"
            f"Website text:\n{cleaned_text}"
        )
        
        try:
            client = get_ai_client()
            request = AIRequest(
                messages=[
                    AIMessage(
                        role="system",
                        content=(
                            "You are a structured data extractor. Output ONLY a valid JSON array. "
                            "No markdown formatting, no code fences, no explanations. "
                            'Example output: [{"name": "John Smith", "role": "Senior Recruiter"}, {"name": "Jane Doe", "role": "Engineering Manager"}]'
                        ),
                    ),
                    AIMessage(role="user", content=prompt),
                ],
                temperature=0.0,
            )
            response = await client.complete(request)
            content = response.content.strip()
            
            logger.info(
                "AI extraction raw response",
                extra={
                    "action": "ai_extraction_response",
                    "source_url": source_url,
                    "ai_response_length": len(content),
                    "ai_response_preview": content[:500],
                    "ai_completion_tokens": response.usage.completion_tokens,
                    "input_text_length": text_length,
                },
            )
            
            # Robust JSON extraction to strip markdown blocks
            content = re.sub(r'^```(?:json)?\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
            content = content.strip()
                
            data = json.loads(content)
            
            if not isinstance(data, list):
                logger.warning(
                    "AI returned non-array response",
                    extra={
                        "action": "ai_extraction_bad_format",
                        "source_url": source_url,
                        "response_type": type(data).__name__,
                        "response_preview": content[:200],
                    },
                )
                return candidates
            
            for item in data:
                if "name" in item and "role" in item:
                    role = normalize_whitespace(item["role"])
                    if classify_role(role) == "other":
                        logger.debug(
                            "Skipping candidate with 'other' role category",
                            extra={
                                "action": "ai_candidate_skipped_other_role",
                                "name": item["name"],
                                "role": role,
                            },
                        )
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

            if not candidates and data:
                # AI found people but all were filtered by classify_role
                logger.warning(
                    "AI found candidates but all were filtered out by role classification",
                    extra={
                        "action": "ai_candidates_all_filtered",
                        "source_url": source_url,
                        "raw_candidates_count": len(data),
                        "raw_candidates": data[:10],
                    },
                )
            elif not candidates:
                logger.warning(
                    "AI returned empty array — no contacts found in text",
                    extra={
                        "action": "ai_extraction_empty",
                        "source_url": source_url,
                        "company_name": company_name,
                        "input_text_length": text_length,
                        "input_text_preview": cleaned_text[:300],
                    },
                )
        except json.JSONDecodeError as e:
            logger.error(
                f"AI response was not valid JSON: {e}",
                extra={
                    "action": "ai_extraction_json_error",
                    "source_url": source_url,
                    "response_preview": content[:500] if 'content' in dir() else "N/A",
                },
            )
        except Exception as e:
            logger.error(
                f"AI candidate extraction failed: {e}",
                extra={
                    "action": "ai_extraction_error",
                    "source_url": source_url,
                    "error": str(e),
                },
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
