from __future__ import annotations

import pytest

from eupago.utils import bic_for_pt_iban


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
