"""Unofficial Python SDK for the eupago payment gateway."""

from eupago._client import EupagoClient
from eupago.exceptions import (
    ApiError,
    AuthenticationError,
    DecryptionError,
    EupagoError,
    NetworkError,
    NotFoundError,
    PaymentError,
    RateLimitError,
    ServiceUnavailableError,
    SignatureError,
    ValidationError,
    WebhookError,
)
from eupago.models import Customer, PaymentResult, PaymentStatus, WebhookEvent

__version__ = "0.1.0"

__all__ = [
    "ApiError",
    "AuthenticationError",
    "Customer",
    "DecryptionError",
    "EupagoClient",
    "EupagoError",
    "NetworkError",
    "NotFoundError",
    "PaymentError",
    "PaymentResult",
    "PaymentStatus",
    "RateLimitError",
    "ServiceUnavailableError",
    "SignatureError",
    "ValidationError",
    "WebhookError",
    "WebhookEvent",
    "__version__",
]
