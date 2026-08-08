from __future__ import annotations

from typing import Any

import pytest
from app.contact_discovery.extractor import PublicContactExtractor
from app.contact_discovery.normalizer import build_dedupe_key, classify_role
from app.main import create_app
from app.schemas.contact import ContactCandidate, ContactDiscoveryRequest, ContactMethod
from app.services.contact import ContactService
from fastapi.testclient import TestClient


class FakeTask:
    id = "task-1"


@pytest.mark.asyncio
async def test_contact_extractor_finds_public_recruiting_contacts() -> None:
    html = """
    <html>
      <body>
        <p>Jane Doe - Technical Recruiter</p>
        <a href="mailto:jane@example.com">Email Jane</a>
        <a href="https://www.linkedin.com/in/janedoe">LinkedIn</a>
      </body>
    </html>
    """

    contacts = await PublicContactExtractor().extract(
        html,
        source_url="https://example.com/team",
        company_name="Example Inc",
    )

    assert len(contacts) == 1
    assert contacts[0].name == "Jane Doe"
    assert contacts[0].role == "Technical Recruiter"
    assert {method.type for method in contacts[0].contact_methods} >= {
        "email",
        "linkedin",
        "source_page",
    }


def test_contact_normalizer_classifies_target_roles() -> None:
    assert classify_role("Senior Technical Recruiter") == "recruiter"
    assert classify_role("Engineering Manager") == "engineering_manager"
    assert classify_role("Hiring Manager") == "hiring_manager"
    assert classify_role("People Operations Partner") == "hr"


def test_contact_dedupe_key_is_stable() -> None:
    candidate = ContactCandidate(
        name="Jane Doe",
        role="Technical Recruiter",
        company_name="Example Inc",
        contact_methods=[ContactMethod(type="email", value="Jane@Example.com")],
        source_url="https://example.com/team",
    )

    assert build_dedupe_key(candidate) == build_dedupe_key(candidate)


def test_contact_routes_are_registered_for_request_validation() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/contacts/not-a-uuid")
    root_response = client.get("/contacts/not-a-uuid")

    assert response.status_code == 422
    assert root_response.status_code == 422


@pytest.mark.asyncio
async def test_contact_discovery_can_enqueue_background_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_enqueue_task(name: str, args: dict[str, Any]) -> FakeTask:
        assert name == "agent_execution"
        assert args["agent_name"] == "contact_discovery"
        assert args["payload"]["company_name"] == "Example Inc"
        return FakeTask()

    monkeypatch.setattr("app.services.contact.enqueue_task", fake_enqueue_task)
    service = ContactService(session=None)  # type: ignore[arg-type]

    response = await service.discover(
        ContactDiscoveryRequest(
            company_name="Example Inc",
            source_urls=["https://example.com/team"],
            run_in_background=True,
        )
    )

    assert response.status == "queued"
    assert response.task_id == "task-1"
