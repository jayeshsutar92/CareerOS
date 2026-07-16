from uuid import uuid4

import pytest
from app.main import create_app
from app.schemas.job import JobCreate, JobUpdate
from fastapi.testclient import TestClient
from pydantic import ValidationError


def test_job_routes_are_reachable_for_request_validation() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/jobs/not-a-uuid")
    root_response = client.get("/jobs/not-a-uuid")

    assert response.status_code == 422
    assert root_response.status_code == 422


def test_job_create_validates_source_url() -> None:
    with pytest.raises(ValidationError):
        JobCreate(company_id=uuid4(), title="Software Engineer", source_url="not-a-url")


def test_job_create_requires_title() -> None:
    with pytest.raises(ValidationError):
        JobCreate(company_id=uuid4(), title="")


def test_job_update_requires_at_least_one_field() -> None:
    with pytest.raises(ValidationError, match="At least one field must be provided"):
        JobUpdate()


def test_job_update_allows_nullable_fields_to_clear_values() -> None:
    payload = JobUpdate(location=None, employment_type=None, source_url=None, posted_at=None)

    assert payload.location is None
    assert payload.employment_type is None
    assert payload.source_url is None
    assert payload.posted_at is None
    assert payload.model_fields_set == {"location", "employment_type", "source_url", "posted_at"}
