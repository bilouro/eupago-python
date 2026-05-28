from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from eupago._http import HttpTransport


class ApiKeyAuth:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def apply_header(self, headers: dict[str, str]) -> dict[str, str]:
        return {**headers, "Authorization": f"ApiKey {self.api_key}"}

    def apply_body(self, body: dict[str, Any]) -> dict[str, Any]:
        return {**body, "chave": self.api_key}


class OAuthAuth:
    _TOKEN_BUFFER_SECONDS = 60

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        transport: HttpTransport,
        auth_path: str = "/api/auth/token",
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._transport = transport
        self._auth_path = auth_path
        self._token: str | None = None
        self._expires_at: float = 0.0

    def _is_expired(self) -> bool:
        return time.monotonic() >= self._expires_at

    def _fetch_token(self) -> str:
        response = self._transport.request(
            "POST",
            self._auth_path,
            json={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "grant_type": "client_credentials",
            },
        )
        data = response.json()
        self._token = data["access_token"]
        expires_in: int = data.get("expires_in", 3600)
        self._expires_at = time.monotonic() + expires_in - self._TOKEN_BUFFER_SECONDS
        return self._token

    async def _fetch_token_async(self) -> str:
        response = await self._transport.request_async(
            "POST",
            self._auth_path,
            json={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "grant_type": "client_credentials",
            },
        )
        data = response.json()
        self._token = data["access_token"]
        expires_in: int = data.get("expires_in", 3600)
        self._expires_at = time.monotonic() + expires_in - self._TOKEN_BUFFER_SECONDS
        return self._token

    def get_token(self) -> str:
        if self._token is None or self._is_expired():
            return self._fetch_token()
        return self._token

    async def get_token_async(self) -> str:
        if self._token is None or self._is_expired():
            return await self._fetch_token_async()
        return self._token

    def apply_header(self, headers: dict[str, str]) -> dict[str, str]:
        return {**headers, "Authorization": f"Bearer {self.get_token()}"}

    async def apply_header_async(self, headers: dict[str, str]) -> dict[str, str]:
        token = await self.get_token_async()
        return {**headers, "Authorization": f"Bearer {token}"}
