"""
MB WAY — Pagamento directo via telemóvel.

O cliente recebe uma notificação push no telemóvel e tem 5 minutos
para aprovar. O resultado chega via webhook.

Fluxo:
  App → create_payment → Cliente aprova no tlm → Webhook (PAID)
"""

from decimal import Decimal

from eupago import EupagoClient, PaymentStatus
from eupago.models import Customer

# 1. Criar o client (sandbox para testes)
client = EupagoClient(
    api_key="xxxx-xxxx-xxxx-xxxx-xxxx",
    sandbox=True,
)

# 2. Criar pagamento MB WAY
payment = client.mbway.create_payment(
    order_id="ORD-2026-001",
    amount=Decimal("49.90"),
    phone_number="351#912345678",  # Formato: 351#9XXXXXXXX
    # Opcional:
    description="Encomenda #001",
    callback_url="https://a-tua-app.pt/webhooks/eupago",
    customer=Customer(email="cliente@email.com"),
)

print(f"Transaction ID: {payment.transaction_id}")
print(f"Status:         {payment.status}")  # PaymentStatus.PENDING
print(f"Montante:       {payment.amount} {payment.currency}")

# 3. Aguardar webhook da eupago (ver exemplo 06_webhook_fastapi.py)
#    Quando o cliente aprovar, recebes status=PAID no webhook.
