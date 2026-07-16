from datetime import timedelta

import pytest
from app.core.security import TokenType, create_token, decode_token, hash_password, verify_password


def test_password_hashing_and_verification() -> None:
    password = "correct-horse-battery-staple"

    hashed_password = hash_password(password)

    assert hashed_password != password
    assert verify_password(password, hashed_password)
    assert not verify_password("wrong-password", hashed_password)


def test_access_token_contains_expected_claims() -> None:
    token = create_token(
        subject="user-id",
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=5),
    )

    payload = decode_token(token)

    assert payload["sub"] == "user-id"
    assert payload["type"] == TokenType.ACCESS
    assert "exp" in payload


def test_invalid_token_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Invalid token"):
        decode_token("not-a-valid-token")
