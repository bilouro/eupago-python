from __future__ import annotations

from eupago._auth import ApiKeyAuth


def test_api_key_apply_header() -> None:
    auth = ApiKeyAuth("demo-1234-5678-9012-3456")
    headers = auth.apply_header({"Accept": "application/json"})
    assert headers["Authorization"] == "ApiKey demo-1234-5678-9012-3456"
    assert headers["Accept"] == "application/json"


def test_api_key_apply_body() -> None:
    auth = ApiKeyAuth("demo-1234-5678-9012-3456")
    body = auth.apply_body({"valor": 10.0})
    assert body["chave"] == "demo-1234-5678-9012-3456"
    assert body["valor"] == 10.0
