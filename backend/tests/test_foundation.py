from app.main import create_app
from fastapi.testclient import TestClient


def test_root_endpoint_preserves_existing_response() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Backend Running"}


def test_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "CareerOS API"
    assert body["environment"] == "development"


def test_api_v1_health_endpoint() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_validation_errors_use_standard_error_shape() -> None:
    app = create_app()

    @app.get("/validation-test")
    async def validation_test(limit: int) -> dict[str, int]:
        return {"limit": limit}

    client = TestClient(app)

    response = client.get("/validation-test", params={"limit": "invalid"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "Request validation failed"
    assert body["error"]["details"]
