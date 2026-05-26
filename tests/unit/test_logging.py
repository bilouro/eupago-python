from __future__ import annotations

from eupago._logging import redact_pii


def test_redacts_phone_number() -> None:
    assert "***PHONE***" in redact_pii("Telefone: 912345678")


def test_redacts_phone_with_country_code() -> None:
    assert "***PHONE***" in redact_pii("Phone: 351#912345678")


def test_redacts_email() -> None:
    assert "***EMAIL***" in redact_pii("Email: user@example.com")


def test_preserves_non_pii_text() -> None:
    text = "Payment ORD-001 completed successfully"
    assert redact_pii(text) == text
