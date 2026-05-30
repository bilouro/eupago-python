"""
Reembolso — Devolver dinheiro ao cliente.

Funciona para qualquer transação paga (MB WAY, Multibanco, Cartão,
Apple/Google Pay, Pay By Link). Total ou parcial.

Requer credenciais OAuth (`client_id` + `client_secret`) — emitidas pelo
suporte eupago mediante pedido. Para testes ou scripts pontuais podes
também injectar directamente um Bearer obtido pelo backoffice login com
``management_bearer=...`` (ver exemplo no fim).

⚠️ O eupago NÃO emite webhook em reembolsos. Confirma pelo retorno:
   ``result.status == PaymentStatus.REFUNDED``.

⚠️ Para Multibanco a refund exige `iban` (e opcionalmente `bic`) — o
   pagamento foi banco-a-banco, logo o reembolso também precisa. Para
   MB WAY e Cartão não.
"""

from decimal import Decimal

from eupago import EupagoClient, PaymentStatus

# --- Production: OAuth client_id + client_secret ---
client = EupagoClient(
    api_key="xxxx-xxxx-xxxx-xxxx-xxxx",
    client_id="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    client_secret="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    sandbox=True,
)

# Reembolso total de MB WAY ou Cartão (sem IBAN)
result = client.refunds.refund(
    transaction_id="29748010",  # eupago transaction_id (do webhook ou da resposta)
    amount=Decimal("3.45"),
    reason="Cliente desistiu",  # opcional
)

if result.status == PaymentStatus.REFUNDED:
    refund_id = result.raw_response["refundId"]  # eupago refund id, para audit
    print(f"Reembolso #{refund_id} OK para {result.transaction_id}")
else:
    print(f"Falhou: {result.raw_response}")


# --- Reembolso de Multibanco (precisa IBAN do cliente) ---

multibanco_refund = client.refunds.refund(
    transaction_id="113068862",
    amount=Decimal("40.00"),
    reason="Devolução produto",
    iban="PT50000201231234567890154",  # IBAN do cliente
    # bic="BACTPTPT",                  # opcional, normalmente desnecessário
)


# --- Reembolso parcial ---

partial = client.refunds.refund(
    transaction_id="29748010",
    amount=Decimal("1.00"),  # menos que o total da transação
    reason="Devolução parcial — 1 item de 3",
)
print(f"Parcial: {partial.status}")


# --- Async ---
#
# async with EupagoClient(api_key="...", client_id="...", client_secret="...") as c:
#     result = await c.refunds.refund_async(
#         transaction_id="29748010", amount=Decimal("3.45"),
#     )


# --- Alternative: usar Bearer pré-obtido (test / scripts) ---
#
# Em vez de OAuth client_id/client_secret podes injectar directamente um
# Bearer obtido pelo backoffice login (mesmo token que a UI do backoffice
# usa para chamar a Management API). Usa isto se ainda não tens OAuth
# provisionado:
#
# from tests.integration.sandbox_backoffice import BackofficeSession
# with BackofficeSession("user@example.com", "password") as s:
#     test_client = EupagoClient(
#         api_key="...",
#         management_bearer=s._bearer,
#         sandbox=True,
#     )
#     test_client.refunds.refund(transaction_id="...", amount=Decimal("..."))
