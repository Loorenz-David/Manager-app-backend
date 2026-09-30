import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from beyo_manager.config import settings
from beyo_manager.routers.utils import jwt_dep


@pytest.mark.unit
async def test_get_jwt_claims_accepts_token_without_exp(monkeypatch) -> None:
    token = jwt.encode(
        {"user_id": "usr_floor", "app_scope": "floor", "jti": "floor-jti"},
        settings.jwt_secret_key,
        algorithm="HS256",
    )

    async def _not_blocklisted(_jti: str) -> bool:
        return False

    monkeypatch.setattr(jwt_dep, "_is_blocklisted", _not_blocklisted)
    jwt_dep._claim_cache.clear()

    claims = await jwt_dep.get_jwt_claims(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    )

    assert claims["jti"] == "floor-jti"
    assert "exp" not in claims


@pytest.mark.unit
def test_token_without_exp_works_on_protected_route(monkeypatch) -> None:
    token = jwt.encode(
        {"user_id": "usr_floor", "app_scope": "floor", "jti": "route-jti"},
        settings.jwt_secret_key,
        algorithm="HS256",
    )

    async def _not_blocklisted(_jti: str) -> bool:
        return False

    monkeypatch.setattr(jwt_dep, "_is_blocklisted", _not_blocklisted)
    jwt_dep._claim_cache.clear()

    app = FastAPI()

    @app.get("/protected")
    async def _protected(claims: dict = Depends(jwt_dep.get_jwt_claims)) -> dict:
        return claims

    response = TestClient(app).get(
        "/protected",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["jti"] == "route-jti"
    assert "exp" not in response.json()


def _protected_client() -> TestClient:
    app = FastAPI()

    @app.get("/protected")
    async def _protected(claims: dict = Depends(jwt_dep.get_jwt_claims)) -> dict:
        return claims

    return TestClient(app)


def _bearer_for(jti: str) -> dict[str, str]:
    token = jwt.encode(
        {"user_id": "usr_manager", "app_scope": "manager", "jti": jti},
        settings.jwt_secret_key,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.unit
def test_blocklist_outage_is_503_auth_unavailable_not_401(monkeypatch) -> None:
    """Cannot validate != invalid: the client must retry, not sign the user out."""

    async def _blocklist_unavailable(_jti: str) -> bool:
        raise ConnectionError("redis unavailable")

    monkeypatch.setattr(jwt_dep.auth, "is_token_blocklisted", _blocklist_unavailable)
    jwt_dep._claim_cache.clear()

    response = _protected_client().get("/protected", headers=_bearer_for("outage-jti"))

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"
    detail = response.json()["detail"]
    assert detail["code"] == "auth_unavailable"
    assert detail["ok"] is False
    assert detail["reason"] == "token_blocklist_unavailable"
    # Fail closed: the unverified token is not cached as good.
    assert not jwt_dep._claim_cache


@pytest.mark.unit
def test_revoked_token_is_still_401(monkeypatch) -> None:
    async def _revoked(_jti: str) -> bool:
        return True

    monkeypatch.setattr(jwt_dep.auth, "is_token_blocklisted", _revoked)
    jwt_dep._claim_cache.clear()

    response = _protected_client().get("/protected", headers=_bearer_for("revoked-jti"))

    assert response.status_code == 401
    assert response.json() == {"detail": "Token has been revoked."}
    assert "Retry-After" not in response.headers


@pytest.mark.unit
def test_invalid_token_is_still_401() -> None:
    jwt_dep._claim_cache.clear()

    response = _protected_client().get(
        "/protected", headers={"Authorization": "Bearer not-a-jwt"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token."}
