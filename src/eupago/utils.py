"""Utility helpers (non-API) used by SDK callers."""

from __future__ import annotations

# Bank-code → BIC lookup for Portuguese IBANs. Used by Multibanco refunds,
# which require a ``bic`` value in addition to ``iban`` (eupago's API rejects
# missing / empty / null bic with ``BIC_INVALID`` — confirmed live in
# production on 2026-05-31).
#
# Best-effort coverage of the major retail banks. The canonical, exhaustive
# list lives at Banco de Portugal:
#   https://www.bportugal.pt/page/codigos-de-instituicao
# Add entries here via PR if you need wider coverage.
_PT_BANK_BIC: dict[str, str] = {
    "0007": "BESTPTPL",  # Banco BEST
    "0010": "BBPIPTPL",  # Banco BPI
    "0018": "TOTAPTPL",  # Banco Santander Totta
    "0019": "BCOMPTPL",  # BCP subsidiary
    "0023": "BBVAPTPL",  # BBVA (historical)
    "0032": "BCOMPTPL",  # BCP subsidiary
    "0033": "BCOMPTPL",  # Millennium BCP
    "0034": "MPIOPTPL",  # Montepio (alt code)
    "0035": "CGDIPTPL",  # Caixa Geral de Depósitos
    "0036": "CGDIPTPL",  # CGD (BNU / Macau)
    "0045": "CCCMPTPL",  # Crédito Agrícola
    "0046": "BESCPTPL",  # Novo Banco (historical BES code)
    "0061": "BMABPTPL",  # Banco Madesant
    "0065": "PPOPPTPL",  # Banco Popular Portugal
    "0079": "BESCPTPL",  # Novo Banco
    "0082": "BCOMPTPL",  # Banco UCI (BCP)
    "0193": "BACAPTPL",  # Banco Atlântico Europa
    "0235": "BAIPPTPL",  # Banco BIC / EuroBic
    "0269": "BEFFPTPL",  # Banco Efisa
    "5780": "MPIOPTPL",  # Caixa Económica Montepio Geral
    "7000": "BCOMPTPL",  # ActivoBank (BCP subsidiary)
}


def bic_for_pt_iban(iban: str) -> str | None:
    """Look up the BIC for a Portuguese IBAN by its bank code.

    The bank code is positions 5-8 of a PT IBAN (``PT50 XXXX YYYY ...``).
    Whitespace in the IBAN is ignored. Returns ``None`` if the bank code is
    not in the bundled lookup table — in that case the caller must obtain
    the BIC from the customer or another source.

    Used primarily for Multibanco refunds, where ``client.refunds.refund(...)``
    requires both ``iban`` and ``bic``::

        from eupago.utils import bic_for_pt_iban

        iban = customer_iban
        bic = bic_for_pt_iban(iban) or ask_customer_for_bic()
        client.refunds.refund(
            transaction_id=trid, amount=amount, iban=iban, bic=bic,
        )
    """
    cleaned = iban.replace(" ", "").upper()
    if not cleaned.startswith("PT") or len(cleaned) < 8:
        return None
    bank_code = cleaned[4:8]
    return _PT_BANK_BIC.get(bank_code)
