"""Utility helpers (non-API) used by SDK callers."""

from __future__ import annotations

from typing import Any

from eupago._logging import redact_pii as _redact_text

# Bank-code → BIC lookup for Portuguese IBANs. Used by Multibanco refunds,
# which require a ``bic`` value in addition to ``iban`` (eupago's API rejects
# missing / empty / null bic with ``BIC_INVALID`` — confirmed live in
# production on 2026-05-31).
#
# Canonical source: Banco de Portugal published list of institution codes
# (https://www.bportugal.pt/page/codigos-de-instituicao). The table below
# covers the institutions active in Portugal — add via PR if you need an
# entry that's missing.
_PT_BANK_BIC: dict[str, str] = {
    "0001": "BGALPTTG",  # Banco de Portugal (central bank)
    "0007": "BESCPTPL",  # Novo Banco (historical Banco Espírito Santo code)
    "0008": "BAIPPTPL",  # Banco BAI Europa
    "0010": "BBPIPTPL",  # Banco BPI
    "0014": "IVVSPTPL",  # Banco Invest
    "0018": "TOTAPTPL",  # Banco Santander Totta
    "0019": "BBVAPTPL",  # BBVA
    "0022": "BRASPTPL",  # Banco do Brasil
    "0023": "ACTVPTPL",  # ActivoBank
    "0033": "BCOMPTPL",  # Millennium BCP
    "0034": "BNPAPTPL",  # BNP Paribas
    "0035": "CGDIPTPL",  # Caixa Geral de Depósitos
    "0036": "MPIOPTPL",  # Montepio
    "0043": "DEUTPTPL",  # Deutsche Bank
    "0045": "CCCMPTPL",  # Crédito Agrícola
    "0047": "ESSIPTPL",  # Banco Espírito Santo de Investimento
    "0048": "BFIAPTPL",  # Banco Finantia
    "0059": "CEMAPTP2",  # Caixa Económica da Misericórdia de Angra do Heroísmo
    "0061": "BDIGPTPL",  # Banco BiG
    "0063": "BNFIPTPL",  # Banco BNI Europa
    "0064": "BPGPPTPL",  # Banco Português de Gestão
    "0065": "BESZPTPL",  # Banco Privado Atlântico
    "0073": "IBNBPTP1",  # Banco Invest (alt code)
    "0079": "BPNPPTPL",  # Banco Português de Negócios
    "0097": "CCCHPTP1",  # Caixa de Crédito Agrícola Mútuo de Chamusca
    "0098": "CERTPTP1",  # Banco Carregosa
    "0160": "BESAPTPA",  # Banco Espírito Santo Açores
    "0169": "CITIPTPX",  # Citibank International
    "0170": "CAGLPTPL",  # Caixa Geral / Banco Caixa Geral
    "0189": "BAPAPTPL",  # Banco Atlântico Europa
    "0191": "BNICPTPL",  # Banco Nacional de Crédito
    "0193": "CTTVPTPL",  # Banco CTT
    "0235": "BLJCPTPT",  # Banco L. J. Carregosa
    "0269": "BKBKPTPL",  # Bankinter Portugal
    "0272": "WZNKPTPL",  # Banco Pichincha / Wise
    "0275": "BSABPTPL",  # Banco Sabadell
    "0500": "BBRUPTPL",  # Banco Bilbao Vizcaya
    "0698": "UIFCPTPT",  # Union Bancaire Privée
    "0781": "IGCPPTPL",  # Agência de Gestão da Tesouraria (IGCP)
    "0848": "CETMPTP1",  # Caixa Económica do Funchal
    "0881": "ONIFPTP1",  # Banco Único / Outros
    "0916": "CRBBPTP1",  # Caixa de Crédito Agrícola Mútuo de Bombarral
    "0921": "CFFIPTP1",  # Caixa de Crédito Agrícola Mútuo
    "3560": "REVOPTP2",  # Revolut
    "5180": "CDCTPTP2",  # Caixa Crédito Mútuo (rural)
    "5200": "CDOTPTPP",  # Caixa Crédito Mútuo
    "5340": "CTIUPTPP",  # Caixa Crédito Mútuo
    "5558": "CGPEESM2",  # Caixa Geral (sucursal)
    "5564": "CAYCESM2",  # Sucursal estrangeira
    "7500": "SONVPTP1",  # Banco Sonangol Portugal
    "7630": "CEODESB1",  # Sucursal estrangeira
    "7837": "PRXBGRAA",  # Sucursal estrangeira
    "8115": "CTTPPTP1",  # CTT Pagamentos
    "8703": "SIAOPTPL",  # SIBS / outros
    "9889": "BSCHESMMGET",  # Santander Empresas
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


def redact_pii(data: Any) -> Any:
    """Return a copy of *data* with PII masked (phone numbers, emails, NIF).

    Uses the same patterns the SDK applies to its own log output (R6):
    9-digit PT phone numbers (with or without ``+351``), email addresses,
    and NIF-shaped numbers become ``***PHONE***`` / ``***EMAIL***`` /
    ``***NIF***``.

    Accepts a string, or any combination of dicts / lists / tuples nested
    inside each other — only string *values* are redacted; keys and
    non-string scalars (numbers, booleans, ``None``) pass through
    untouched. The input is never mutated.

    The primary use case is persisting raw webhook / API payloads for
    audit without building up a store of personal data::

        from eupago.utils import redact_pii

        event_row["raw"] = redact_pii(webhook_body)  # then INSERT

    See the "Persisting payments" recipe in the docs for the full
    storage pattern.
    """
    if isinstance(data, str):
        return _redact_text(data)
    if isinstance(data, dict):
        return {key: redact_pii(value) for key, value in data.items()}
    if isinstance(data, (list, tuple)):
        return type(data)(redact_pii(value) for value in data)
    return data
