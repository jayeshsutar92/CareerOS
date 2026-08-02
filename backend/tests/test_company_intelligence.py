from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.company_intelligence.agent import CompanyIntelligenceAgent, register_company_intelligence_agent
from app.company_intelligence.extractor import CompanyIntelligenceExtractor, CompanyWebsiteFetcher
from app.company_intelligence.summarizer import CompanyIntelligenceSummarizer
from app.company_intelligence.tech_signatures import TechStackDetector
from app.main import create_app
from app.models.company_intelligence import CompanyIntelligence, IntelligenceStatus
from app.repositories.company_intelligence import CompanyIntelligenceRepository
from app.schemas.company_intelligence import CompanyIntelligenceRequest
from app.services.company_intelligence import CompanyIntelligenceService
from fastapi.testclient import TestClient


class FakeTask:
    id = "task-comp-intel-10"


def test_tech_stack_detector():
    detector = TechStackDetector()
    sample_html = """
    <html>
      <head>
        <script src="https://cdn.example.com/_next/static/chunks/main.js"></script>
        <script src="https://js.stripe.com/v3/"></script>
        <meta name="generator" content="FastAPI" />
      </head>
      <body class="flex bg-gray-100 hidden">
        <h1>Welcome</h1>
      </body>
    </html>
    """
    detected = detector.detect(sample_html)
    assert "Next.js" in detected
    assert "Stripe" in detected
    assert "Tailwind CSS" in detected
    assert "FastAPI" in detected


def test_company_extractor():
    extractor = CompanyIntelligenceExtractor()
    sample_html = """
    <html>
      <head>
        <title>Acme Corp - Innovating AI</title>
        <meta name="description" content="Acme Corp provides state of the art AI platforms." />
      </head>
      <body>
        <h1>Building the Future of Automation</h1>
        <p>Acme Corp is a technology company delivering software automation across global industries.</p>
        <a href="/about-us">About Us</a>
        <a href="/careers">Jobs at Acme</a>
        <a href="mailto:contact@acme.com">Email Us</a>
        <a href="https://linkedin.com/company/acmecorp">LinkedIn</a>
      </body>
    </html>
    """
    raw = extractor.extract(sample_html, base_url="https://acme.com")
    assert raw["title"] == "Acme Corp - Innovating AI"
    assert raw["meta_description"] == "Acme Corp provides state of the art AI platforms."
    assert "https://acme.com/about-us" in raw["about_url"]
    assert "https://acme.com/careers" in raw["careers_url"]
    assert "contact@acme.com" in raw["contact_info"]["emails"]
    assert "https://linkedin.com/company/acmecorp" in raw["contact_info"]["socials"].values()


@pytest.mark.asyncio
async def test_summarizer_rule_based_fallback():
    summarizer = CompanyIntelligenceSummarizer()
    raw = {
        "domain_name": "Acme",
        "meta_description": "Acme Corp provides state of the art AI platforms.",
        "headings": ["Products & Solutions", "AI Platform"],
        "paragraphs": ["Acme Corp is a technology company."],
        "tech_stack": ["FastAPI", "React"],
    }
    summary = await summarizer.summarize(raw)
    assert summary["overview"] == "Acme Corp provides state of the art AI platforms."
    assert "Products & Solutions" in summary["products_services"]
    assert "Acme overview:" in summary["summary"]


@pytest.mark.asyncio
async def test_service_analyze_sync():
    session = AsyncMock()
    service = CompanyIntelligenceService(session)
    mock_html = "<html><head><title>Test Corp</title></head><body><h1>Header</h1></body></html>"

    fake_intelligence = MagicMock(spec=CompanyIntelligence)
    fake_intelligence.id = "11111111-1111-1111-1111-111111111111"
    fake_intelligence.company_id = None
    fake_intelligence.company_name = "Test Corp"
    fake_intelligence.website_url = "https://testcorp.com"
    fake_intelligence.overview = "Overview"
    fake_intelligence.products_services = []
    fake_intelligence.tech_stack = ["FastAPI"]
    fake_intelligence.careers_url = None
    fake_intelligence.about_url = None
    fake_intelligence.contact_info = {}
    fake_intelligence.raw_content = {}
    fake_intelligence.raw_summary = "Summary"
    fake_intelligence.status = IntelligenceStatus.COMPLETED
    fake_intelligence.error = None
    fake_intelligence.analysis_version = 1
    fake_intelligence.last_analyzed_at = None
    fake_intelligence.created_at = "2026-08-02T00:00:00Z"
    fake_intelligence.updated_at = "2026-08-02T00:00:00Z"

    with patch.object(CompanyWebsiteFetcher, "fetch_page", new_callable=AsyncMock) as mock_fetch, \
         patch.object(CompanyIntelligenceRepository, "upsert", new_callable=AsyncMock) as mock_upsert:

        mock_fetch.return_value = (mock_html, {"server": "nginx"})
        mock_upsert.return_value = fake_intelligence

        payload = CompanyIntelligenceRequest(
            website_url="https://testcorp.com", company_name="Test Corp"
        )
        response = await service.analyze(payload)
        assert response.status == "completed"
        assert response.data is not None
        assert response.data.company_name == "Test Corp"


@pytest.mark.asyncio
async def test_service_can_enqueue_background_job(monkeypatch: pytest.MonkeyPatch):
    async def fake_enqueue_task(name: str, args: dict):
        assert name == "agent_execution"
        assert args["agent_name"] == "company_intelligence"
        return FakeTask()

    monkeypatch.setattr("app.services.company_intelligence.enqueue_task", fake_enqueue_task)
    service = CompanyIntelligenceService(session=AsyncMock())

    response = await service.analyze(
        CompanyIntelligenceRequest(
            website_url="https://testcorp.com",
            run_in_background=True,
        )
    )

    assert response.status == "queued"
    assert response.task_id == "task-comp-intel-10"


def test_agent_registration():
    register_company_intelligence_agent()
    agent = CompanyIntelligenceAgent()
    assert agent.name == "company_intelligence"


def test_api_routes_reachability():
    client = TestClient(create_app())
    response = client.get("/api/v1/company-intelligence/invalid-uuid")
    assert response.status_code == 422
