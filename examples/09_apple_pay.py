"""
Apple Pay — Pagamento via Apple Wallet.

Dois fluxos:

**Hospedado (recomendado para web)** — omites o token e o eupago devolve
um ``payment_url``: rediriges o browser do cliente para lá e é o eupago
que serve a Apple Pay sheet. Não precisas de conta Apple Developer.

**Nativo (apps iOS / web com Merchant ID próprio)** — obténs um
``PKPaymentToken`` no cliente (Touch ID / Face ID) e encaminha-lo no
``apple_pay_token``; o eupago desencripta e cobra sem redirect.

Fluxo hospedado:
  App → create_payment → recebes payment_url
  → Redirect do browser do cliente → Apple Pay sheet na página eupago
  → Webhook (PAID/DECLINED)
"""

from decimal import Decimal

from eupago import EupagoClient
from eupago.models import Customer

client = EupagoClient(api_key="xxxx-xxxx-xxxx-xxxx-xxxx", sandbox=True)

# Fluxo hospedado — sem token. O eupago serve a Apple Pay sheet.
payment = client.apple_pay.create_payment(
    order_id="ORD-AP-2026-001",
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
# Requer Apple Developer Merchant ID + domain verification. O token vem do
# frontend (window.ApplePaySession / PassKit) e é opaco para o SDK:
#
# apple_pay_token = '{"paymentMethod":"...","paymentData":{"version":"EC_v1",...}}'
# payment = client.apple_pay.create_payment(
#     order_id="ORD-AP-2026-002",
#     amount=Decimal("39.90"),
#     apple_pay_token=apple_pay_token,
# )


# --- Reembolso ---
#
# refund = client.refunds.refund(
#     transaction_id=payment.transaction_id,
#     amount=Decimal("39.90"),
# )
