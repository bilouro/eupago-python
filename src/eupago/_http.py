from __future__ import annotations

import asyncio
import platform
import random
import time
from typing import Any, Callable

import httpx

from eupago._config import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    INITIAL_RETRY_DELAY,
    MAX_RETRY_DELAY,
)
from eupago._logging import logger
from eupago.exceptions import (
    ApiError,
    AuthenticationError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
)

AuditHook = Callable[[httpx.Request, httpx.Response, float], Any]


def _user_agent(version: str) -> str:
    return f"eupago-python/{version} (Python/{platform.python_version()})"


class HttpTransport:
    def __init__(
        self,
        *,
        base_url: str,
        version: str = "0.0.0",
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._max_retries = max_retries
        self._audit_hook: AuditHook | None = None
        self._ua = _user_agent(version)

        self._sync_client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            headers={"User-Agent": self._ua, "Content-Type": "application/json"},
        )
        self._async_client: httpx.AsyncClient | None = None

    def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={"User-Agent": self._ua, "Content-Type": "application/json"},
            )
        return self._async_client

    def set_audit_hook(self, hook: AuditHook | None) -> None:
        self._audit_hook = hook

    def _should_retry(self, method: str, response: httpx.Response | None, attempt: int) -> bool:
        if attempt >= self._max_retries:
            return False
        if method.upper() != "GET":
            return False
        if response is None:
            return True
        return response.status_code >= 500

    def _retry_delay(self, attempt: int) -> float:
        delay = min(INITIAL_RETRY_DELAY * (2**attempt), MAX_RETRY_DELAY)
        jitter: float = delay * (0.5 + random.random() * 0.5)  # noqa: S311
        return jitter

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return

        try:
            data = response.json()
        except Exception:
            data = {}

        message = str(
            data.get("message") or data.get("Message") or data.get("resposta") or response.text
        )
        error_code_raw = data.get("code") or data.get("estado")
        error_code = int(error_code_raw) if error_code_raw is not None else None

        kwargs: dict[str, Any] = {
            "status_code": response.status_code,
            "error_code": error_code,
        }

        if response.status_code == 401:
            raise AuthenticationError(message)
        if response.status_code == 404:
            raise NotFoundError(message, **kwargs)
        if response.status_code == 429:
            raise RateLimitError(message, **kwargs)
        if response.status_code >= 500:
            raise ServiceUnavailableError(message, **kwargs)
        raise ApiError(message, **kwargs)

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                start = time.monotonic()
                response = self._sync_client.request(
                    method,
                    path,
                    json=json,
                    params=params,
                    headers=headers or {},
                )
                duration_ms = (time.monotonic() - start) * 1000
                logger.debug(
                    "HTTP %s %s → %d (%.0fms)", method, path, response.status_code, duration_ms
                )

                if self._audit_hook is not None:
                    self._audit_hook(response.request, response, duration_ms)

                if response.status_code >= 400:
                    if self._should_retry(method, response, attempt):
                        time.sleep(self._retry_delay(attempt))
                        continue
                    self._raise_for_status(response)

                return response

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_exc = exc
                logger.debug(
                    "HTTP %s %s → %s (attempt %d)", method, path, type(exc).__name__, attempt + 1
                )
                if self._should_retry(method, None, attempt):
                    time.sleep(self._retry_delay(attempt))
                    continue
                raise NetworkError(str(exc)) from exc

        raise NetworkError(str(last_exc)) from last_exc

    async def request_async(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        client = self._get_async_client()
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                start = time.monotonic()
                response = await client.request(
                    method,
                    path,
                    json=json,
                    params=params,
                    headers=headers or {},
                )
                duration_ms = (time.monotonic() - start) * 1000
                logger.debug(
                    "HTTP %s %s → %d (%.0fms)", method, path, response.status_code, duration_ms
                )

                if self._audit_hook is not None:
                    self._audit_hook(response.request, response, duration_ms)

                if response.status_code >= 400:
                    if self._should_retry(method, response, attempt):
                        await asyncio.sleep(self._retry_delay(attempt))
                        continue
                    self._raise_for_status(response)

                return response

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_exc = exc
                logger.debug(
                    "HTTP %s %s → %s (attempt %d)", method, path, type(exc).__name__, attempt + 1
                )
                if self._should_retry(method, None, attempt):
                    await asyncio.sleep(self._retry_delay(attempt))
                    continue
                raise NetworkError(str(exc)) from exc

        raise NetworkError(str(last_exc)) from last_exc

    def close(self) -> None:
        self._sync_client.close()

    async def aclose(self) -> None:
        self._sync_client.close()
        if self._async_client is not None:
            await self._async_client.aclose()
