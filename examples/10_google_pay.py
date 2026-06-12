"""
Google Pay — Pagamento via Google Pay.

Dois fluxos:

**Hospedado (recomendado para web)** — omites o token e o eupago devolve
um ``payment_url``: rediriges o browser do cliente para lá e é o eupago
que serve a Google Pay sheet. Não precisas de merchant id próprio.

**Nativo (apps Android / web com merchant id próprio)** — obténs um token
``PaymentData`` no cliente e encaminha-lo no ``google_pay_token``; o
eupago desencripta e cobra sem redirect.

Fluxo hospedado:
  App → create_payment → recebes payment_url
  → Redirect do browser do cliente → Google Pay sheet na página eupago
  → Webhook (PAID/DECLINED)
"""

from decimal import Decimal

from eupago import EupagoClient
from eupago.models import Customer

client = EupagoClient(api_key="xxxx-xxxx-xxxx-xxxx-xxxx", sandbox=True)

# Fluxo hospedado — sem token. O eupago serve a Google Pay sheet.
payment = client.google_pay.create_payment(
    order_id="ORD-GP-2026-001",
    amount=Decimal("39.90"),
    description="Encomenda #001",
    customer=Customer(email="cliente@email.com"),
    success_url="https://loja.exemplo/checkout/ok",
    error_url="https://loja.exemplo/checkout/fail",
)

print(f"Transaction ID: {payment.transaction_id}")
print(f"Redirect to:    {payment.payment_url}")  # envia o browser para aqui
# Confirmação final via webhook


# --- Fluxo nativo (avançado) ---
#
# Requer merchant configurado no Google Pay & Wallet Console. O token vem
# do frontend (PaymentsClient.loadPaymentData) e é opaco para o SDK:
#
# google_pay_token = '{"paymentMethodData":{"tokenizationData":{"token":"..."}}}'
# payment = client.google_pay.create_payment(
#     order_id="ORD-GP-2026-002",
#     amount=Decimal("39.90"),
#     google_pay_token=google_pay_token,
# )


# --- Reembolso ---
#
# refund = client.refunds.refund(
#     transaction_id=payment.transaction_id,
#     amount=Decimal("39.90"),
# )
