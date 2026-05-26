from __future__ import annotations

from eupago import EupagoClient
from eupago.services.mbway import MBWayService


def test_client_creates_with_api_key() -> None:
    client = EupagoClient(api_key="test-key", sandbox=True)
    assert isinstance(client.mbway, MBWayService)
    client.close()


def test_client_sandbox_url() -> None:
    client = EupagoClient(api_key="test-key", sandbox=True)
    assert "sandbox" in client._transport._base_url
    client.close()


def test_client_production_url() -> None:
    client = EupagoClient(api_key="test-key", sandbox=False)
    assert "clientes" in client._transport._base_url
    client.close()


def test_client_lazy_service_caching() -> None:
    client = EupagoClient(api_key="test-key", sandbox=True)
    mbway1 = client.mbway
    mbway2 = client.mbway
    assert mbway1 is mbway2
    client.close()


def test_client_context_manager() -> None:
    with EupagoClient(api_key="test-key", sandbox=True) as client:
        assert isinstance(client.mbway, MBWayService)
