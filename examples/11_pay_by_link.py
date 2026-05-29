"""
Pay By Link — Gerar link de pagamento.

Um único link onde o cliente escolhe como pagar (MB WAY, Multibanco, Cartão,
Apple/Google Pay, Cofidis…). Não precisas de site nem checkout próprios —
ideal para facturas, vendas por Instagram/WhatsApp, B2B avulso.

Fluxo:
  App → create_payment → recebes payment_url
  → Envias o link ao cliente (email / SMS / WhatsApp / QR code)
  → Cliente abre, escolhe método e paga na página eupago
  → Webhook (PAID)
"""

from datetime import datetime, timedelta
from decimal import Decimal

from eupago import EupagoClient
from eupago.models import Customer

client = EupagoClient(api_key="xxxx-xxxx-xxxx-xxxx-xxxx", sandbox=True)

# Caso simples — link que expira daqui a 7 dias
link = client.pay_by_link.create_payment(
    order_id="FAT-2026-001",
    amount=Decimal("199.00"),
    customer=Customer(
        name="Joana Silva",
        email="joana@cliente.pt",
        notify=True,  # eupago envia o link por email automaticamente
    ),
    expires_at=datetime.now() + timedelta(days=7),
)

print(f"Link de pagamento: {link.payment_url}")
print(f"Transaction ID:    {link.transaction_id}")

# Envia o link.payment_url ao cliente (email/SMS/WhatsApp). Quando ele
# completar o pagamento na página eupago, recebes um webhook PAID com o
# order_id "FAT-2026-001".


# --- Caso avançado: link com produtos + portes + redirects ---

shopping_cart = client.pay_by_link.create_payment(
    order_id="ORD-2026-099",
    amount=Decimal("125.00"),
    shipping=Decimal("5.50"),  # Portes mostrados separadamente
    success_url="https://a-tua-loja.pt/obrigado",
    error_url="https://a-tua-loja.pt/falha",
    back_url="https://a-tua-loja.pt/carrinho",
    expires_at=datetime.now() + timedelta(hours=24),
    products=[
        {"sku": "BOOK-1", "name": "Guia de Pilates", "value": 60.00, "quantity": 2},
        {"sku": "MAT-1", "name": "Mat antiderrapante", "value": 5.00, "quantity": 1},
    ],
    customer=Customer(name="Cliente Final", email="cliente@email.com"),
)
print(f"Carrinho → {shopping_cart.payment_url}")


# --- Reembolso ---
#
# refund = client.refunds.refund(
#     transaction_id=link.transaction_id,
#     value=Decimal("199.00"),
# )
