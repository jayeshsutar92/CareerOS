from __future__ import annotations

import json
import logging
from typing import Any

from app.ai.client import get_ai_client
from app.ai.models import AIMessage, AIRequest
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class CompanyIntelligenceSummarizer:
    async def summarize(self, raw_content: dict[str, Any]) -> dict[str, Any]:
        """Summarize company information using AI infrastructure with rule-based fallback."""
        try:
            return await self._summarize_ai(raw_content)
        except Exception as exc:
            logger.warning(
                "AI summarization skipped or failed, falling back to rule-based summary",
                extra={"error": str(exc)},
            )
            return self._summarize_rule_based(raw_content)

    async def _summarize_ai(self, raw_content: dict[str, Any]) -> dict[str, Any]:
        settings = get_settings()
        if not settings.grok_api_key and not settings.ai_provider:
            raise ValueError("No AI provider configured")

        ai_client = get_ai_client()
        prompt_text = (
            "Analyze the following extracted company website information and return a JSON object with strictly these keys:\n"
            "- 'overview': concise 2-3 sentence company overview\n"
            "- 'products_services': array of string key products or services offered\n"
            "- 'summary': executive summary paragraph suitable for personalization in job applications / outreach emails\n\n"
            f"Extracted Information:\n{json.dumps(raw_content, indent=2)}"
        )

        request = AIRequest(
            messages=[
                AIMessage(
                    role="system",
                    content="You are an expert company intelligence analyst. Respond ONLY with valid JSON.",
                ),
                AIMessage(role="user", content=prompt_text),
            ],
            temperature=0.2,
        )

        response = await ai_client.complete(request)
        content = response.content.strip()

        # Clean JSON markdown fences if present
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        parsed = json.loads(content)
        return {
            "overview": parsed.get("overview") or self._extract_fallback_overview(raw_content),
            "products_services": parsed.get("products_services") or self._extract_fallback_products(raw_content),
            "summary": parsed.get("summary") or self._extract_fallback_summary(raw_content),
        }

    def _summarize_rule_based(self, raw_content: dict[str, Any]) -> dict[str, Any]:
        overview = self._extract_fallback_overview(raw_content)
        products_services = self._extract_fallback_products(raw_content)
        summary = self._extract_fallback_summary(raw_content)

        return {
            "overview": overview,
            "products_services": products_services,
            "summary": summary,
        }

    def _extract_fallback_overview(self, raw_content: dict[str, Any]) -> str:
        meta_desc = raw_content.get("meta_description")
        if meta_desc:
            return meta_desc
        title = raw_content.get("title")
        domain = raw_content.get("domain_name", "The company")
        if title:
            return f"{domain} - {title}."
        paragraphs = raw_content.get("paragraphs", [])
        if paragraphs:
            return paragraphs[0]
        return f"{domain} provides software and services."

    def _extract_fallback_products(self, raw_content: dict[str, Any]) -> list[str]:
        headings = raw_content.get("headings", [])
        products: list[str] = []
        for h in headings:
            if any(word in h.lower() for word in ["product", "service", "platform", "solution", "feature", "build", "tool"]):
                products.append(h)
        if not products and headings:
            products = headings[:3]
        return products

    def _extract_fallback_summary(self, raw_content: dict[str, Any]) -> str:
        domain = raw_content.get("domain_name", "The company")
        overview = self._extract_fallback_overview(raw_content)
        tech = raw_content.get("tech_stack", [])
        tech_str = f" Known tech stack includes: {', '.join(tech)}." if tech else ""
        return f"{domain} overview: {overview}{tech_str}"
