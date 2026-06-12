from __future__ import annotations

import pytest

from eupago.utils import bic_for_pt_iban, redact_pii


@pytest.mark.parametrize(
    ("iban", "expected"),
    [
        # Live-verified during 2026-05-31 prod refund — Millennium BCP
        ("PT50003300004561332142005", "BCOMPTPL"),
        # Same with spaces (real-world copy-paste)
        ("PT50 0033 0000 45613321420 05", "BCOMPTPL"),
        # Lowercase
        ("pt50003300004561332142005", "BCOMPTPL"),
        # Other major PT banks
        ("PT50001000001234567890154", "BBPIPTPL"),  # BPI
        ("PT50001800001234567890154", "TOTAPTPL"),  # Santander Totta
        ("PT50002300001234567890154", "ACTVPTPL"),  # ActivoBank
        ("PT50003400001234567890154", "BNPAPTPL"),  # BNP Paribas
        ("PT50003500001234567890154", "CGDIPTPL"),  # CGD
        ("PT50003600001234567890154", "MPIOPTPL"),  # Montepio
        ("PT50004500001234567890154", "CCCMPTPL"),  # Crédito Agrícola
        ("PT50019300001234567890154", "CTTVPTPL"),  # Banco CTT
        ("PT50026900001234567890154", "BKBKPTPL"),  # Bankinter
        ("PT50356000001234567890154", "REVOPTP2"),  # Revolut
        ("PT50016900001234567890154", "CITIPTPX"),  # Citibank
    ],
)
def test_bic_for_pt_iban_known_banks(iban: str, expected: str) -> None:
    assert bic_for_pt_iban(iban) == expected


def test_bic_for_pt_iban_unknown_bank_returns_none() -> None:
    assert bic_for_pt_iban("PT50999900001234567890154") is None


def test_bic_for_pt_iban_non_pt_returns_none() -> None:
    assert bic_for_pt_iban("ES9121000418450200051332") is None


def test_bic_for_pt_iban_too_short_returns_none() -> None:
    assert bic_for_pt_iban("PT50") is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("call 912345678 now", "call ***PHONE*** now"),
        ("+351 912345678", "+351 ***PHONE***"),  # digits masked; prefix may remain
        ("mail me at user@example.com", "mail me at ***EMAIL***"),
        ("NIF 123 456 789 ok", "NIF ***NIF*** ok"),
        ("no pii here", "no pii here"),
    ],
)
def test_redact_pii_string(text: str, expected: str) -> None:
    assert redact_pii(text) == expected


def test_redact_pii_nested_webhook_payload() -> None:
    body = {
        "channel": {"account": "demo"},
        "transaction": {
            "identifier": "ORD-001",
            "amount": {"value": "49.90", "currency": "EUR"},
            "customerPhone": "912345678",
            "trid": 78901,
        },
        "customer": {"email": "cliente@email.com", "notify": True},
        "tags": ["912345678", "safe"],
    }
    redacted = redact_pii(body)

    assert redacted["transaction"]["customerPhone"] == "***PHONE***"
    assert redacted["customer"]["email"] == "***EMAIL***"
    assert redacted["tags"] == ["***PHONE***", "safe"]
    # Non-string scalars pass through untouched
    assert redacted["transaction"]["trid"] == 78901
    assert redacted["customer"]["notify"] is True
    # Non-PII strings unchanged
    assert redacted["transaction"]["identifier"] == "ORD-001"
    assert redacted["transaction"]["amount"]["currency"] == "EUR"


def test_redact_pii_does_not_mutate_input() -> None:
    original = {"customer": {"email": "user@example.com"}}
    redact_pii(original)
    assert original["customer"]["email"] == "user@example.com"


def test_redact_pii_tuple_preserves_type() -> None:
    result = redact_pii(("912345678", 1))
    assert isinstance(result, tuple)
    assert result == ("***PHONE***", 1)
