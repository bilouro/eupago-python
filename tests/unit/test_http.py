from __future__ import annotations

import pytest
import respx
from httpx import Response

from eupago._http import HttpTransport
from eupago.exceptions import (
    AuthenticationError,
    NotFoundError,
    ServiceUnavailableError,
)


@pytest.fixture
def transport() -> HttpTransport:
    return HttpTransport(
        base_url="https://sandbox.eupago.pt",
        version="0.1.0-test",
        timeout=5.0,
        max_retries=1,
    )


@respx.mock
def test_successful_request(transport: HttpTransport) -> None:
    respx.get("https://sandbox.eupago.pt/test").mock(return_value=Response(200, json={"ok": True}))
    response = transport.request("GET", "/test")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


@respx.mock
def test_user_agent_header(transport: HttpTransport) -> None:
    route = respx.get("https://sandbox.eupago.pt/test").mock(return_value=Response(200, json={}))
    transport.request("GET", "/test")
    assert "eupago-python/0.1.0-test" in route.calls[0].request.headers["user-agent"]


@respx.mock
def test_401_raises_authentication_error(transport: HttpTransport) -> None:
    respx.get("https://sandbox.eupago.pt/test").mock(
        return_value=Response(401, json={"message": "Invalid key"})
    )
    with pytest.raises(AuthenticationError, match="Invalid key"):
        transport.request("GET", "/test")


@respx.mock
def test_404_raises_not_found_error(transport: HttpTransport) -> None:
    respx.get("https://sandbox.eupago.pt/test").mock(
        return_value=Response(404, json={"message": "Not found"})
    )
    with pytest.raises(NotFoundError):
        transport.request("GET", "/test")


@respx.mock
def test_get_retries_on_500(transport: HttpTransport) -> None:
    route = respx.get("https://sandbox.eupago.pt/test")
    route.side_effect = [
        Response(500, json={"message": "Internal error"}),
        Response(200, json={"ok": True}),
    ]
    response = transport.request("GET", "/test")
    assert response.status_code == 200
    assert len(route.calls) == 2


@respx.mock
def test_post_never_retries_on_500(transport: HttpTransport) -> None:
    respx.post("https://sandbox.eupago.pt/test").mock(
        return_value=Response(500, json={"message": "Internal error"})
    )
    with pytest.raises(ServiceUnavailableError):
        transport.request("POST", "/test", json={"data": "value"})


@respx.mock
def test_audit_hook_called(transport: HttpTransport) -> None:
    calls: list[float] = []
    transport.set_audit_hook(lambda req, resp, ms: calls.append(ms))

    respx.get("https://sandbox.eupago.pt/test").mock(return_value=Response(200, json={}))
    transport.request("GET", "/test")
    assert len(calls) == 1
    assert calls[0] >= 0


@respx.mock
@pytest.mark.asyncio
async def test_async_successful_request(transport: HttpTransport) -> None:
    respx.get("https://sandbox.eupago.pt/test").mock(
        return_value=Response(200, json={"async": True})
    )
    response = await transport.request_async("GET", "/test")
    assert response.json() == {"async": True}
    await transport.aclose()
