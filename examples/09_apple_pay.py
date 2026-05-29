"""
Apple Pay — Pagamento via Apple Wallet.

O Apple Pay devolve um ``PKPaymentToken`` JSON após o utilizador escolher
o cartão na Wallet (Touch ID / Face ID). O servidor encaminha esse token
para o eupago, que o desencripta e processa o pagamento do cartão.

Fluxo:
  Browser/iOS → Apple Pay sheet → token → POST para o teu servidor
  → Servidor → create_payment(apple_pay_token=token) → Webhook (PAID/DECLINED)

Pré-requisitos: app/site configurado no Apple Developer + domain verification
do eupago no Apple Pay (ver eupago.atlassian.net/Apple Pay setup).
"""

from decimal import Decimal

from eupago import EupagoClient
from eupago.models import Customer

client = EupagoClient(api_key="xxxx-xxxx-xxxx-xxxx-xxxx", sandbox=True)

# Token vindo do frontend (PKPaymentToken) — opaco para nós
apple_pay_token = '{"paymentMethod":"...","paymentData":{"version":"EC_v1",...}}'

payment = client.apple_pay.create_payment(
    order_id="ORD-AP-2026-001",
    amount=Decimal("39.90"),
    apple_pay_token=apple_pay_token,
    description="Encomenda #001",
    customer=Customer(email="cliente@email.com"),
)

print(f"Transaction ID: {payment.transaction_id}")
print(f"Status:         {payment.status}")  # PENDING ou PAID
# Confirmação final via webhook


# --- Reembolso ---
#
# refund = client.refunds.refund(
#     transaction_id=payment.transaction_id,
#     value=Decimal("39.90"),
# )
