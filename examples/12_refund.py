"""
Reembolso — Devolver dinheiro ao cliente.

Funciona para qualquer transação paga (MB WAY, Multibanco, Cartão,
Apple/Google Pay, Pay By Link). Total ou parcial.

Requer credenciais OAuth (`client_id` + `client_secret`) — estas NÃO são
a API Key e não estão no backoffice. São emitidas pelo suporte eupago
mediante pedido (suporte@eupago.pt).

⚠️ O eupago NÃO emite webhook em reembolsos. Confirma pelo retorno:
   ``result.status == PaymentStatus.REFUNDED``.
"""

from decimal import Decimal

from eupago import EupagoClient, PaymentStatus

# Configurar OAuth no client
client = EupagoClient(
    api_key="xxxx-xxxx-xxxx-xxxx-xxxx",
    client_id="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    client_secret="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    sandbox=True,
)

# Reembolso total
result = client.refunds.refund(
    transaction_id="113068862",  # ID da transação original
    value=Decimal("64.00"),  # mesmo valor da transação
    reason="Cliente desistiu",  # opcional, fica no histórico
)

if result.status == PaymentStatus.REFUNDED:
    print(f"Reembolso confirmado para {result.transaction_id}")
else:
    print(f"Falhou: {result.raw_response}")


# --- Reembolso parcial ---

partial = client.refunds.refund(
    transaction_id="113068862",
    value=Decimal("20.00"),  # menos que o valor total
    reason="Devolução parcial — 1 item de 3",
)
print(f"Parcial: {partial.status}")


# --- Async ---
#
# async with EupagoClient(api_key="...", client_id="...", client_secret="...") as c:
#     result = await c.refunds.refund_async(
#         transaction_id="113068862", value=Decimal("64.00"),
#     )
