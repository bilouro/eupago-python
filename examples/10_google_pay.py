"""
Google Pay — Pagamento via Google Pay API.

O Google Pay devolve um ``PaymentData`` JSON após o utilizador escolher
o cartão. O servidor encaminha esse token para o eupago, que o desencripta
e processa o pagamento.

Fluxo:
  Browser/Android → Google Pay sheet → token → POST para o teu servidor
  → Servidor → create_payment(google_pay_token=token) → Webhook (PAID/DECLINED)

Pré-requisitos: merchant configurado no Google Pay & Wallet Console.
"""

from decimal import Decimal

from eupago import EupagoClient
from eupago.models import Customer

client = EupagoClient(api_key="xxxx-xxxx-xxxx-xxxx-xxxx", sandbox=True)

# Token vindo do frontend (PaymentData)
google_pay_token = '{"paymentMethodData":{"tokenizationData":{"token":"..."}}}'

payment = client.google_pay.create_payment(
    order_id="ORD-GP-2026-001",
    amount=Decimal("39.90"),
    google_pay_token=google_pay_token,
    description="Encomenda #001",
    customer=Customer(email="cliente@email.com"),
)

print(f"Transaction ID: {payment.transaction_id}")
print(f"Status:         {payment.status}")  # PENDING ou PAID


# --- Reembolso ---
#
# refund = client.refunds.refund(
#     transaction_id=payment.transaction_id,
#     value=Decimal("39.90"),
# )
