from __future__ import annotations

import pytest
import respx
from httpx import Response

from eupago._auth import ApiKeyAuth, OAuthAuth
from eupago._http import HttpTransport
from eupago.exceptions import AuthenticationError
from eupago.services._base import BaseService


@pytest.fixture
def transport() -> HttpTransport:
    return HttpTransport(base_url="https://sandbox.eupago.pt", version="test")


@pytest.fixture
def auth() -> ApiKeyAuth:
    return ApiKeyAuth("test-key")


@respx.mock
def test_service_body_auth(transport: HttpTransport, auth: ApiKeyAuth) -> None:
    route = respx.post("https://sandbox.eupago.pt/test").mock(
        return_value=Response(200, json={"ok": True})
    )

    service = BaseService(transport, auth)
    service._default_auth = "body"
    service._request("POST", "/test", json={"valor": 10})

    import json

    body = json.loads(route.calls[0].request.content)
    assert body["chave"] == "test-key"
    assert body["valor"] == 10


@respx.mock
def test_service_header_auth(transport: HttpTransport, auth: ApiKeyAuth) -> None:
    route = respx.post("https://sandbox.eupago.pt/test").mock(return_value=Response(200, json={}))

    service = BaseService(transport, auth)
    service._request("POST", "/test", json={"data": "x"})

    assert route.calls[0].request.headers["authorization"] == "ApiKey test-key"


def test_service_oauth_without_credentials_raises(
    transport: HttpTransport, auth: ApiKeyAuth
) -> None:
    service = BaseService(transport, auth, oauth=None)
    with pytest.raises(AuthenticationError, match="Management API authentication"):
        service._request("POST", "/test", auth="oauth")


@respx.mock
def test_service_oauth_auth(transport: HttpTransport, auth: ApiKeyAuth) -> None:
    respx.post("https://sandbox.eupago.pt/api/auth/token").mock(
        return_value=Response(200, json={"access_token": "tok", "expires_in": 3600})
    )
    route = respx.post("https://sandbox.eupago.pt/test").mock(return_value=Response(200, json={}))

    oauth = OAuthAuth("cid", "csecret", transport)
    service = BaseService(transport, auth, oauth=oauth)
    service._request("POST", "/test", auth="oauth")

    assert "Bearer tok" in route.calls[0].request.headers["authorization"]


@respx.mock
@pytest.mark.asyncio
async def test_service_async_header_auth(transport: HttpTransport, auth: ApiKeyAuth) -> None:
    route = respx.post("https://sandbox.eupago.pt/test").mock(return_value=Response(200, json={}))

    service = BaseService(transport, auth)
    await service._request_async("POST", "/test", json={"x": 1})

    assert route.calls[0].request.headers["authorization"] == "ApiKey test-key"
    await transport.aclose()


@pytest.mark.asyncio
async def test_service_async_oauth_without_credentials_raises(
    transport: HttpTransport, auth: ApiKeyAuth
) -> None:
    service = BaseService(transport, auth, oauth=None)
    with pytest.raises(AuthenticationError, match="Management API authentication"):
        await service._request_async("POST", "/test", auth="oauth")
    await transport.aclose()


@respx.mock
@pytest.mark.asyncio
async def test_service_async_oauth_auth(transport: HttpTransport, auth: ApiKeyAuth) -> None:
    respx.post("https://sandbox.eupago.pt/api/auth/token").mock(
        return_value=Response(200, json={"access_token": "async-tok", "expires_in": 3600})
    )
    route = respx.post("https://sandbox.eupago.pt/test").mock(return_value=Response(200, json={}))

    oauth = OAuthAuth("cid", "csecret", transport)
    service = BaseService(transport, auth, oauth=oauth)
    await service._request_async("POST", "/test", auth="oauth")

    assert "Bearer async-tok" in route.calls[0].request.headers["authorization"]
    await transport.aclose()
