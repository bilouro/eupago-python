from __future__ import annotations

import pytest
import respx
from httpx import Response

from eupago._auth import OAuthAuth
from eupago._http import HttpTransport


@pytest.fixture
def transport() -> HttpTransport:
    return HttpTransport(base_url="https://sandbox.eupago.pt", version="test")


@respx.mock
def test_oauth_fetches_token(transport: HttpTransport) -> None:
    respx.post("https://sandbox.eupago.pt/api/auth/token").mock(
        return_value=Response(200, json={"access_token": "tok-123", "expires_in": 3600})
    )

    oauth = OAuthAuth("cid", "csecret", transport)
    token = oauth.get_token()

    assert token == "tok-123"


@respx.mock
def test_oauth_caches_token(transport: HttpTransport) -> None:
    route = respx.post("https://sandbox.eupago.pt/api/auth/token").mock(
        return_value=Response(200, json={"access_token": "tok-456", "expires_in": 3600})
    )

    oauth = OAuthAuth("cid", "csecret", transport)
    oauth.get_token()
    oauth.get_token()

    assert len(route.calls) == 1


@respx.mock
def test_oauth_refreshes_expired_token(transport: HttpTransport) -> None:
    route = respx.post("https://sandbox.eupago.pt/api/auth/token").mock(
        return_value=Response(200, json={"access_token": "tok-new", "expires_in": 0})
    )

    oauth = OAuthAuth("cid", "csecret", transport)
    oauth.get_token()
    oauth.get_token()

    assert len(route.calls) == 2


@respx.mock
def test_oauth_apply_header(transport: HttpTransport) -> None:
    respx.post("https://sandbox.eupago.pt/api/auth/token").mock(
        return_value=Response(200, json={"access_token": "bearer-tok", "expires_in": 3600})
    )

    oauth = OAuthAuth("cid", "csecret", transport)
    headers = oauth.apply_header({})

    assert headers["Authorization"] == "Bearer bearer-tok"


@respx.mock
@pytest.mark.asyncio
async def test_oauth_async_fetches_token(transport: HttpTransport) -> None:
    respx.post("https://sandbox.eupago.pt/api/auth/token").mock(
        return_value=Response(200, json={"access_token": "async-tok", "expires_in": 3600})
    )

    oauth = OAuthAuth("cid", "csecret", transport)
    token = await oauth.get_token_async()

    assert token == "async-tok"
    await transport.aclose()


@respx.mock
@pytest.mark.asyncio
async def test_oauth_async_apply_header(transport: HttpTransport) -> None:
    respx.post("https://sandbox.eupago.pt/api/auth/token").mock(
        return_value=Response(200, json={"access_token": "async-bearer", "expires_in": 3600})
    )

    oauth = OAuthAuth("cid", "csecret", transport)
    headers = await oauth.apply_header_async({})

    assert headers["Authorization"] == "Bearer async-bearer"
    await transport.aclose()
