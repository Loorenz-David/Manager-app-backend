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
