from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from eupago._auth import ApiKeyAuth, OAuthAuth, StaticBearerAuth
    from eupago._http import HttpTransport


class BaseService:
    _default_auth: str = "header"

    def __init__(
        self,
        transport: HttpTransport,
        auth: ApiKeyAuth,
        oauth: OAuthAuth | StaticBearerAuth | None = None,
    ) -> None:
        self._transport = transport
        self._auth = auth
        self._oauth = oauth

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        auth: str | None = None,
    ) -> httpx.Response:
        auth_type = auth or self._default_auth
        headers: dict[str, str] = {}
        body = dict(json) if json else {}

        if auth_type == "header":
            headers = self._auth.apply_header(headers)
        elif auth_type == "body":
            body = self._auth.apply_body(body)
        elif auth_type == "oauth":
            if self._oauth is None:
                from eupago.exceptions import AuthenticationError

                raise AuthenticationError(
                    "Management API authentication required — pass either "
                    "client_id/client_secret (OAuth) or management_bearer "
                    "to EupagoClient."
                )
            headers = self._oauth.apply_header(headers)

        return self._transport.request(
            method,
            path,
            json=body if body else None,
            data=data,
            params=params,
            headers=headers,
        )

    async def _request_async(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        auth: str | None = None,
    ) -> httpx.Response:
        auth_type = auth or self._default_auth
        headers: dict[str, str] = {}
        body = dict(json) if json else {}

        if auth_type == "header":
            headers = self._auth.apply_header(headers)
        elif auth_type == "body":
            body = self._auth.apply_body(body)
        elif auth_type == "oauth":
            if self._oauth is None:
                from eupago.exceptions import AuthenticationError

                raise AuthenticationError(
                    "Management API authentication required — pass either "
                    "client_id/client_secret (OAuth) or management_bearer "
                    "to EupagoClient."
                )
            headers = await self._oauth.apply_header_async(headers)

        return await self._transport.request_async(
            method,
            path,
            json=body if body else None,
            data=data,
            params=params,
            headers=headers,
        )
