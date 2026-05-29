"""
Cartão de Crédito — Pagamento com 3D-Secure.

O cliente é redirecionado para a página da eupago para introduzir os dados
do cartão e (se aplicável) completar o desafio 3DS / OTP. O resultado final
chega via webhook.

Fluxo:
  App → create_payment → redirect cliente para payment_url
  → Cliente preenche cartão na página eupago → 3DS challenge se >500 EUR
  → Webhook (PAID / DECLINED)

Cartão de teste (sandbox): 4018810000150015 | OTP 0101 sucesso, 3333 falha
"""

from decimal import Decimal

from eupago import EupagoClient
from eupago.models import Customer

client = EupagoClient(api_key="xxxx-xxxx-xxxx-xxxx-xxxx", sandbox=True)

# As três URLs de retorno são obrigatórias — o eupago exige-as
payment = client.credit_card.create_payment(
    order_id="ORD-CC-2026-001",
    amount=Decimal("249.90"),
    success_url="https://a-tua-loja.pt/checkout/ok",  # Após pagamento OK
    error_url="https://a-tua-loja.pt/checkout/erro",  # Após pagamento KO
    back_url="https://a-tua-loja.pt/carrinho",  # Botão "Voltar"
    description="Encomenda #2026-001",
    customer=Customer(email="cliente@email.com", notify=True),
)

print(f"Transaction ID: {payment.transaction_id}")
print(f"Redirect URL:   {payment.payment_url}")  # Levar cliente para esta URL
print(f"Status:         {payment.status}")  # PENDING — confirmação por webhook


# --- Authorize + Capture (reservar agora, cobrar depois) ---
#
# Útil para pré-autorizações (ex: reservas) onde só queres cobrar quando o
# serviço for prestado.

auth = client.credit_card.authorize(
    order_id="ORD-CC-AUTH-001",
    amount=Decimal("100.00"),
    success_url="https://a-tua-loja.pt/checkout/ok",
    error_url="https://a-tua-loja.pt/checkout/erro",
    back_url="https://a-tua-loja.pt/carrinho",
)

# Mais tarde — quando o serviço for prestado:
captured = client.credit_card.capture(transaction_id=auth.transaction_id)
print(f"Captura: {captured.status}")  # PAID


# --- Reembolso ---
#
# Reembolsar o pagamento (total ou parcial). Requer credenciais OAuth — ver
# `examples/12_refund.py`.
#
# refund = client.refunds.refund(
#     transaction_id=payment.transaction_id,
#     value=Decimal("249.90"),
#     reason="Cliente desistiu",
# )
