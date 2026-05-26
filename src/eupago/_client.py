from __future__ import annotations

from typing import Any

from eupago._auth import ApiKeyAuth, OAuthAuth
from eupago._config import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    PRODUCTION_BASE_URL,
    SANDBOX_BASE_URL,
)
from eupago._http import AuditHook, HttpTransport
from eupago.services.mbway import MBWayService
from eupago.services.multibanco import MultibancoService


class EupagoClient:
    def __init__(
        self,
        api_key: str,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        sandbox: bool = False,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        from eupago import __version__

        base_url = SANDBOX_BASE_URL if sandbox else PRODUCTION_BASE_URL

        self._transport = HttpTransport(
            base_url=base_url,
            version=__version__,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._auth = ApiKeyAuth(api_key)
        self._oauth: OAuthAuth | None = None

        if client_id and client_secret:
            self._oauth = OAuthAuth(client_id, client_secret, self._transport)

        self._services: dict[str, Any] = {}

    def _get_service(self, name: str, cls: type[Any]) -> Any:
        if name not in self._services:
            self._services[name] = cls(self._transport, self._auth, self._oauth)
        return self._services[name]

    @property
    def mbway(self) -> MBWayService:
        return self._get_service("mbway", MBWayService)  # type: ignore[no-any-return]

    @property
    def multibanco(self) -> MultibancoService:
        return self._get_service("multibanco", MultibancoService)  # type: ignore[no-any-return]

    def set_audit_hook(self, hook: AuditHook | None) -> None:
        self._transport.set_audit_hook(hook)

    def close(self) -> None:
        self._transport.close()

    async def aclose(self) -> None:
        await self._transport.aclose()

    def __enter__(self) -> EupagoClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    async def __aenter__(self) -> EupagoClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()
