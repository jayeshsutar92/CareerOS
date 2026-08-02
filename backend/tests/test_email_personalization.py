from unittest.mock import AsyncMock, patch
import uuid

import pytest
from fastapi.testclient import TestClient

from app.email_personalization.agent import EmailPersonalizationAgent, register_email_personalization_agent
from app.email_personalization.engine import EmailPersonalizationEngine
from app.email_personalization.validator import EmailPersonalizationValidator
from app.main import create_app
from app.schemas.email_personalization import (
    CompanyContext,
    EmailPersonalizationRequest,
    PortfolioLinkContext,
    RecipientContext,
    UserProfileContext,
)
from app.services.email_personalization import EmailPersonalizationService


class FakeTask:
    id = "task-email-personalization-11"


def test_validator_detects_unreplaced_placeholders():
    validator = EmailPersonalizationValidator()
    subject = "Hi [Name], quick thought on [Company]"
    body = "Hello [Name],\n\nI built a project for [Company].\n\nBest,\n[Your Name]"

    is_valid, score, warnings = validator.validate(subject, body)
    assert not is_valid
    assert score < 0.6
    assert any("Unreplaced placeholders" in w for w in warnings)


def test_validator_passes_clean_email():
    validator = EmailPersonalizationValidator()
    subject = "Quick thought on Acme's high-concurrency architecture"
    body = (
        "Hi Alex,\n\n"
        "Saw Acme's latest engineering blog post about Redis rate-limiting under high load.\n\n"
        "I recently built FairQueue, a distributed booking engine that handles seat-locking race conditions "
        "using Redis TTL locks and WebSockets (FastAPI, Redis, Docker).\n\n"
        "I would love to compare notes on how your team is approaching distributed locking.\n\n"
        "Best,\nJayesh Sutar"
    )

    is_valid, score, warnings = validator.validate(subject, body)
    assert is_valid
    assert score >= 0.9
    assert len(warnings) == 0


@pytest.mark.asyncio
async def test_engine_fallback_generation():
    engine = EmailPersonalizationEngine()
    template = (
        "Subject: Quick question for [Name] at [Company]\n\n"
        "Hi [Name],\n\n"
        "I saw [Company]'s product. Check my projects: [GitHub].\n\n"
        "Best,\n[Your name]"
    )

    req = EmailPersonalizationRequest(
        template_content=template,
        template_name="The Builder",
        user_profile=UserProfileContext(name="Jayesh Sutar"),
        company_intelligence=CompanyContext(company_name="Acme Inc"),
        portfolio_links=[PortfolioLinkContext(title="FairQueue", url="https://github.com/jayesh/fairqueue")],
        recipient=RecipientContext(name="Sarah", role="Engineering Manager"),
    )

    result = await engine.generate(req)
    assert result.is_valid
    assert "Sarah" in result.body
    assert "Acme Inc" in result.body
    assert "Jayesh Sutar" in result.body
    assert "https://github.com/jayesh/fairqueue" in result.body
    assert result.status == "draft"


@pytest.mark.asyncio
async def test_service_generate_sync():
    session = AsyncMock()
    service = EmailPersonalizationService(session)

    template = "Hi [Name], I noticed [Company]'s work. Best, [Your name]"
    req = EmailPersonalizationRequest(
        template_content=template,
        user_profile=UserProfileContext(name="Jayesh Sutar"),
        company_intelligence=CompanyContext(company_name="TechCorp"),
        recipient=RecipientContext(name="David"),
        save_draft=False,
    )

    resp = await service.generate(req)
    assert resp.status == "completed"
    assert resp.data is not None
    assert "David" in resp.data.body
    assert "TechCorp" in resp.data.body


@pytest.mark.asyncio
async def test_service_can_enqueue_background_job(monkeypatch: pytest.MonkeyPatch):
    async def fake_enqueue_task(name: str, args: dict):
        assert name == "agent_execution"
        assert args["agent_name"] == "email_personalization"
        return FakeTask()

    monkeypatch.setattr("app.services.email_personalization.enqueue_task", fake_enqueue_task)
    service = EmailPersonalizationService(session=AsyncMock())

    response = await service.generate(
        EmailPersonalizationRequest(
            template_content="Hi [Name], let's connect regarding [Company]. Best, [Your name]",
            run_in_background=True,
        )
    )

    assert response.status == "queued"
    assert response.task_id == "task-email-personalization-11"


def test_agent_registration():
    register_email_personalization_agent()
    agent = EmailPersonalizationAgent()
    assert agent.name == "email_personalization"


def test_api_email_personalization_route_validation():
    client = TestClient(create_app())
    # Request missing mandatory template_content field
    response = client.post("/api/v1/email-personalization/generate", json={})
    assert response.status_code == 422
