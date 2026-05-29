from __future__ import annotations

from typing import Union

from eupago.exceptions import WebhookError
from eupago.models.webhook import WebhookEvent
from eupago.webhooks._parser import parse_body, parse_v1, parse_v2
from eupago.webhooks._signature import decrypt_payload, verify_signature


def parse_webhook(
    *,
    body: Union[bytes, str] | None = None,
    query_params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    webhook_secret: str | None = None,
) -> WebhookEvent:
    headers = {k.lower(): v for k, v in (headers or {}).items()}

    if query_params:
        return parse_v1(query_params)

    if body is None:
        raise WebhookError("Either body or query_params must be provided")

    raw_body = body.encode() if isinstance(body, str) else body

    if webhook_secret and "x-signature" in headers:
        verify_signature(raw_body, headers["x-signature"], webhook_secret)

    data = parse_body(raw_body)

    if "data" in data and webhook_secret and "x-initialization-vector" in headers:
        iv = headers["x-initialization-vector"]
        decrypted = decrypt_payload(data["data"], webhook_secret, iv)
        data = parse_body(decrypted)

    return parse_v2(data)


class Webhooks:
    """Namespace bound to an ``EupagoClient`` that carries the channel's
    ``webhook_secret`` so callers don't pass it on every call.

    The same instance handles both **cleartext** and **encrypted** webhooks —
    encryption is auto-detected from the payload (the ``X-Initialization-Vector``
    header + the ``{"data": "..."}`` body shape). The caller does **not** need
    to declare which mode the channel is configured in.

    Usage::

        client = EupagoClient(api_key="…", webhook_secret="…")
        event = client.webhooks.parse(body=request_body, headers=request_headers)

    Pass ``webhook_secret`` to ``.parse(...)`` to override the client default
    (e.g. when handling webhooks from multiple channels with different secrets).
    """

    def __init__(self, webhook_secret: str | None = None) -> None:
        self._webhook_secret = webhook_secret

    def parse(
        self,
        *,
        body: Union[bytes, str] | None = None,
        query_params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        webhook_secret: str | None = None,
    ) -> WebhookEvent:
        return parse_webhook(
            body=body,
            query_params=query_params,
            headers=headers,
            webhook_secret=webhook_secret if webhook_secret is not None else self._webhook_secret,
        )


__all__ = ["Webhooks", "parse_webhook", "verify_signature"]
