from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.ai.client import get_ai_client
from app.ai.models import AIMessage, AIRequest
from app.core.config import get_settings
from app.email_personalization.validator import EmailPersonalizationValidator
from app.schemas.email_personalization import EmailPersonalizationRead, EmailPersonalizationRequest

logger = logging.getLogger(__name__)


class EmailPersonalizationEngine:
    def __init__(self, validator: EmailPersonalizationValidator | None = None) -> None:
        self.validator = validator or EmailPersonalizationValidator()

    async def generate(self, payload: EmailPersonalizationRequest) -> EmailPersonalizationRead:
        """Personalize email template using AI infrastructure with rule-based fallback & validation."""
        try:
            raw_result = await self._generate_ai(payload)
        except Exception as exc:
            logger.warning(
                "AI email personalization skipped or failed, falling back to rule-based template engine",
                extra={"error": str(exc)},
            )
            raw_result = self._generate_fallback(payload)

        is_valid, confidence_score, warnings = self.validator.validate(
            subject=raw_result["subject"], body=raw_result["body"]
        )

        return EmailPersonalizationRead(
            subject=raw_result["subject"],
            body=raw_result["body"],
            personalized_hooks=raw_result.get("personalized_hooks", []),
            confidence_score=confidence_score,
            is_valid=is_valid,
            validation_warnings=warnings,
            template_name=payload.template_name,
            status="draft",
        )

    async def _generate_ai(self, payload: EmailPersonalizationRequest) -> dict[str, Any]:
        settings = get_settings()
        if not settings.grok_api_key and not settings.ai_provider:
            raise ValueError("No AI provider configured")

        ai_client = get_ai_client()

        context_dict: dict[str, Any] = {
            "template_content": payload.template_content,
            "template_name": payload.template_name,
            "applicant": {
                "name": payload.user_profile.name if payload.user_profile else "Applicant",
                "role": payload.user_profile.current_role if payload.user_profile else None,
                "bio": payload.user_profile.bio_summary if payload.user_profile else None,
                "skills": payload.user_profile.skills if payload.user_profile else [],
            },
            "portfolio_projects": [p.model_dump() for p in payload.portfolio_links],
            "resume_link": payload.resume_link,
            "target_company": payload.company_intelligence.model_dump()
            if payload.company_intelligence
            else None,
            "recipient": payload.recipient.model_dump() if payload.recipient else None,
            "custom_instructions": payload.custom_instructions,
        }

        system_prompt = (
            "You are a world-class executive tech recruiter and cold email strategist. "
            "Your task is to take a provided reference email template and adapt it into a highly personalized, "
            "concise (<180 words), high-converting outreach email targeted at the recipient and company.\n\n"
            "Guidelines:\n"
            "- Never leave generic placeholders like [Name], [Company], [Your Name], or {{...}}.\n"
            "- Highlight proof over promises: reference specific user portfolio projects, tech stack alignments, or company challenges.\n"
            "- Maintain an authentic, professional, developer-to-developer tone.\n"
            "- Return strictly a JSON object with keys:\n"
            "  - 'subject': high-converting email subject line (5-10 words)\n"
            "  - 'body': personalized email body (plain text, formatted with line breaks)\n"
            "  - 'personalized_hooks': array of 2-3 specific personalizations used\n"
        )

        user_prompt = f"Personalization Request:\n{json.dumps(context_dict, indent=2)}"

        request = AIRequest(
            messages=[
                AIMessage(role="system", content=system_prompt),
                AIMessage(role="user", content=user_prompt),
            ],
            temperature=0.3,
        )

        response = await ai_client.complete(request)
        content = response.content.strip()

        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        parsed = json.loads(content)
        return {
            "subject": parsed.get("subject", "Cold Email Outreach"),
            "body": parsed.get("body", payload.template_content),
            "personalized_hooks": parsed.get("personalized_hooks", []),
        }

    def _generate_fallback(self, payload: EmailPersonalizationRequest) -> dict[str, Any]:
        """Rule-based fallback template placeholder resolver."""
        body = payload.template_content
        subject = "Outreach regarding opportunities"

        recipient_name = (payload.recipient.name if payload.recipient and payload.recipient.name else None) or "there"
        company_name = (
            payload.company_intelligence.company_name
            if payload.company_intelligence and payload.company_intelligence.company_name
            else "your team"
        )
        user_name = payload.user_profile.name if payload.user_profile else "Applicant"

        # Build portfolio string
        portfolio_str = ""
        if payload.portfolio_links:
            first_project = payload.portfolio_links[0]
            portfolio_str = f"{first_project.title} ({first_project.url})"
            if len(payload.portfolio_links) > 1:
                portfolio_str += f" and {payload.portfolio_links[1].title} ({payload.portfolio_links[1].url})"
        elif payload.resume_link:
            portfolio_str = str(payload.resume_link)

        # Replacements
        replacements = [
            (re.compile(r"\[Name\]", re.I), recipient_name),
            (re.compile(r"\[Company\]", re.I), company_name),
            (re.compile(r"\[Your name\]|\[Your Name\]", re.I), user_name),
            (re.compile(r"\[GitHub\]|\[Portfolio\]", re.I), portfolio_str or "portfolio"),
            (re.compile(r"\[Email\]", re.I), "my contact email"),
        ]

        for pattern, replacement in replacements:
            body = pattern.sub(replacement, body)

        # Extract Subject line if template contains "Subject: ..."
        subject_match = re.search(r"Subject:\s*(.+)", body)
        if subject_match:
            subject = subject_match.group(1).strip()
            body = re.sub(r"Subject:\s*.+\n*", "", body).strip()
        else:
            subject = f"Connecting with {company_name}"

        hooks = [
            f"Addressed to {recipient_name} at {company_name}",
            f"Referenced applicant name '{user_name}'",
        ]
        if portfolio_str:
            hooks.append(f"Included portfolio references: {portfolio_str}")

        return {
            "subject": subject,
            "body": body,
            "personalized_hooks": hooks,
        }
