import pytest
from app.main import create_app
from app.schemas.company import CompanyCreate, CompanyUpdate
from fastapi.testclient import TestClient
from pydantic import ValidationError


def test_company_routes_are_reachable_for_request_validation() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/companies/not-a-uuid")
    root_response = client.get("/companies/not-a-uuid")

    assert response.status_code == 422
    assert root_response.status_code == 422


def test_company_create_validates_url() -> None:
    with pytest.raises(ValidationError):
        CompanyCreate(name="Acme", website_url="not-a-url")


def test_company_update_requires_at_least_one_field() -> None:
    with pytest.raises(ValidationError, match="At least one field must be provided"):
        CompanyUpdate()


def test_company_update_allows_nullable_fields_to_clear_values() -> None:
    payload = CompanyUpdate(website_url=None, description=None)

    assert payload.website_url is None
    assert payload.description is None
    assert payload.model_fields_set == {"website_url", "description"}
