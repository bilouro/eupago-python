"""
Apple Pay e Google Pay — Pagamento com wallet digital.

Endpoints simples: gera um URL, redireciona o cliente, pagamento imediato.
Sem auth/capture, sem subscriptions.
"""

from decimal import Decimal

from eupago import EupagoClient
from eupago.models import Customer

client = EupagoClient(api_key="xxxx-xxxx-xxxx-xxxx-xxxx", sandbox=True)


# --- Apple Pay ---

apple = client.apple_pay.create_payment(
    order_id="ORD-APPLE-001",
    amount=Decimal("29.99"),
    success_url="https://loja.pt/pagamento/ok",
    error_url="https://loja.pt/pagamento/erro",
    callback_url="https://loja.pt/webhooks/eupago",
    customer=Customer(email="cliente@email.com"),
)

print(f"Apple Pay URL: {apple.payment_url}")
# Redirecionar cliente para apple.payment_url


# --- Google Pay ---

google = client.google_pay.create_payment(
    order_id="ORD-GOOGLE-001",
    amount=Decimal("35.00"),
    success_url="https://loja.pt/pagamento/ok",
    error_url="https://loja.pt/pagamento/erro",
    callback_url="https://loja.pt/webhooks/eupago",
)

print(f"Google Pay URL: {google.payment_url}")
# Redirecionar cliente para google.payment_url
