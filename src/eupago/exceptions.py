from __future__ import annotations


class EupagoError(Exception):
    """Base exception for all eupago SDK errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class AuthenticationError(EupagoError):
    """Invalid API key or expired OAuth token."""


class ValidationError(EupagoError):
    """Invalid parameters detected before calling the API."""


class ApiError(EupagoError):
    """Error response from the eupago API."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: int | str | None = None,
        request_id: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.request_id = request_id
        super().__init__(message)

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code is not None:
            parts.append(f"HTTP {self.status_code}")
        if self.error_code is not None:
            parts.append(f"code={self.error_code}")
        if self.request_id:
            parts.append(f"request_id={self.request_id}")
        return " | ".join(parts)


class PaymentError(ApiError):
    """Payment failed or was declined."""


class RateLimitError(ApiError):
    """Request was rate limited."""


class NotFoundError(ApiError):
    """Reference or transaction not found."""


class ServiceUnavailableError(ApiError):
    """eupago API is unavailable."""


class WebhookError(EupagoError):
    """Webhook processing error."""


class SignatureError(WebhookError):
    """Invalid HMAC signature on webhook."""


class DecryptionError(WebhookError):
    """Failed to decrypt encrypted webhook payload."""


class NetworkError(EupagoError):
    """Network-level error: timeout, connection refused, DNS failure."""
