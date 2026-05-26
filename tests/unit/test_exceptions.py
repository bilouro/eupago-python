from __future__ import annotations

from eupago.exceptions import (
    ApiError,
    AuthenticationError,
    EupagoError,
    NetworkError,
    NotFoundError,
    PaymentError,
    RateLimitError,
    ServiceUnavailableError,
    SignatureError,
    WebhookError,
)


def test_exception_hierarchy() -> None:
    assert issubclass(AuthenticationError, EupagoError)
    assert issubclass(ApiError, EupagoError)
    assert issubclass(PaymentError, ApiError)
    assert issubclass(RateLimitError, ApiError)
    assert issubclass(NotFoundError, ApiError)
    assert issubclass(ServiceUnavailableError, ApiError)
    assert issubclass(WebhookError, EupagoError)
    assert issubclass(SignatureError, WebhookError)
    assert issubclass(NetworkError, EupagoError)


def test_api_error_str() -> None:
    err = ApiError("something failed", status_code=400, error_code=-9, request_id="req-123")
    result = str(err)
    assert "something failed" in result
    assert "HTTP 400" in result
    assert "code=-9" in result
    assert "request_id=req-123" in result


def test_api_error_str_minimal() -> None:
    err = ApiError("fail")
    assert str(err) == "fail"
