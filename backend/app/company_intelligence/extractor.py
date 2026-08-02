from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.company_intelligence.tech_signatures import TechStackDetector

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3})?[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})")
LINKEDIN_RE = re.compile(r"https?://(?:[\w]+\.)?linkedin\.com/company/[\w\-/%]+", re.I)
TWITTER_RE = re.compile(r"https?://(?:[\w]+\.)?(?:twitter|x)\.com/[\w\-/%]+", re.I)
GITHUB_RE = re.compile(r"https?://(?:[\w]+\.)?github\.com/[\w\-/%]+", re.I)


class CompanyWebsiteFetcher:
    def __init__(self, timeout_seconds: float = 15.0) -> None:
        self.timeout_seconds = timeout_seconds

    async def fetch_page(self, url: str) -> tuple[str, dict[str, str]]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 "
                "CareerOS Company Intelligence/1.0"
            )
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            resp_headers = {k.lower(): v for k, v in response.headers.items()}
            return response.text, resp_headers


class CompanyIntelligenceExtractor:
    def __init__(self, tech_detector: TechStackDetector | None = None) -> None:
        self.tech_detector = tech_detector or TechStackDetector()

    def extract(
        self,
        html: str,
        base_url: str,
        headers: dict[str, str] | None = None,
        about_html: str | None = None,
        careers_html: str | None = None,
    ) -> dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()

        title = self._extract_title(soup)
        meta_desc = self._extract_meta_description(soup)
        headings = self._extract_headings(soup)
        key_paragraphs = self._extract_key_paragraphs(soup)
        about_url, careers_url = self._discover_subpage_urls(soup, base_url)

        # Detect Tech Stack
        combined_html = html + (" " + about_html if about_html else "") + (" " + careers_html if careers_html else "")
        tech_stack = self.tech_detector.detect(combined_html, headers)

        # Extract Contacts & Social Links
        contact_info = self._extract_contact_info(combined_html, base_url, soup)

        # Fallback company name from domain if title is generic
        parsed_url = urlparse(base_url)
        domain_name = parsed_url.netloc.removeprefix("www.").split(".")[0].capitalize()

        raw_content: dict[str, Any] = {
            "base_url": base_url,
            "domain_name": domain_name,
            "title": title,
            "meta_description": meta_desc,
            "headings": headings,
            "paragraphs": key_paragraphs,
            "about_url": about_url,
            "careers_url": careers_url,
            "tech_stack": tech_stack,
            "contact_info": contact_info,
        }

        if about_html:
            about_soup = BeautifulSoup(about_html, "html.parser")
            for tag in about_soup(["script", "style", "noscript"]):
                tag.decompose()
            raw_content["about_text"] = about_soup.get_text("\n", strip=True)[:2000]

        if careers_html:
            careers_soup = BeautifulSoup(careers_html, "html.parser")
            for tag in careers_soup(["script", "style", "noscript"]):
                tag.decompose()
            raw_content["careers_text"] = careers_soup.get_text("\n", strip=True)[:2000]

        return raw_content

    def _extract_title(self, soup: BeautifulSoup) -> str:
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return str(og_title["content"]).strip()
        return ""

    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            return str(meta_desc["content"]).strip()
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            return str(og_desc["content"]).strip()
        return ""

    def _extract_headings(self, soup: BeautifulSoup) -> list[str]:
        headings: list[str] = []
        for tag in soup.find_all(["h1", "h2"]):
            text = tag.get_text(strip=True)
            if text and len(text) > 3 and text not in headings:
                headings.append(text[:150])
        return headings[:10]

    def _extract_key_paragraphs(self, soup: BeautifulSoup) -> list[str]:
        paragraphs: list[str] = []
        for p in soup.find_all("p"):
            text = p.get_text(" ", strip=True)
            if len(text) > 40 and text not in paragraphs:
                paragraphs.append(text[:300])
        return paragraphs[:8]

    def _discover_subpage_urls(self, soup: BeautifulSoup, base_url: str) -> tuple[str | None, str | None]:
        about_url: str | None = None
        careers_url: str | None = None

        for a in soup.find_all("a", href=True):
            href = str(a["href"]).strip()
            text = a.get_text(strip=True).lower()

            full_url = urljoin(base_url, href)
            if not about_url and any(kw in href.lower() or kw in text for kw in ["about", "about-us", "company"]):
                about_url = full_url
            if not careers_url and any(kw in href.lower() or kw in text for kw in ["career", "careers", "jobs", "join-us"]):
                careers_url = full_url

        return about_url, careers_url

    def _extract_contact_info(self, html: str, base_url: str, soup: BeautifulSoup) -> dict[str, Any]:
        emails: set[str] = set(EMAIL_RE.findall(html))
        phones: set[str] = set(PHONE_RE.findall(html))
        socials: dict[str, str] = {}

        for link in LINKEDIN_RE.findall(html):
            socials["linkedin"] = link.rstrip("/")
        for link in TWITTER_RE.findall(html):
            socials["twitter"] = link.rstrip("/")
        for link in GITHUB_RE.findall(html):
            socials["github"] = link.rstrip("/")

        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            if href.startswith("mailto:"):
                clean_email = href.removeprefix("mailto:").split("?")[0]
                if clean_email:
                    emails.add(clean_email)

        # Filter unhelpful generic phone string matches
        valid_phones = [p.strip() for p in phones if len(p.strip()) >= 7 and not p.startswith("123")]

        return {
            "emails": sorted(emails)[:5],
            "phones": valid_phones[:3],
            "socials": socials,
        }
