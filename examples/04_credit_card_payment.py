"""
Cartão de Crédito — Pagamento directo com 3D Secure.

O SDK gera um URL de pagamento. Redireciona o cliente para esse URL
onde ele preenche os dados do cartão num formulário seguro da eupago.
Após pagamento, é redirecionado de volta.

Fluxo:
  App → create_payment → Redireciona cliente para paymentUrl
  → Cliente preenche cartão + 3D Secure → Webhook (PAID)
  → Cliente redirecionado para successUrl
"""

from decimal import Decimal

from eupago import EupagoClient
from eupago.models import Customer

client = EupagoClient(api_key="xxxx-xxxx-xxxx-xxxx-xxxx", sandbox=True)

# Criar pagamento por cartão
payment = client.credit_card.create_payment(
    order_id="ORD-2026-004",
    amount=Decimal("99.99"),             # Máximo: 3.999 EUR
    success_url="https://loja.pt/pagamento/ok",       # Cliente vai aqui após pagar
    error_url="https://loja.pt/pagamento/erro",       # Cliente vai aqui se falhar
    cancel_url="https://loja.pt/pagamento/cancelado",  # Cliente vai aqui se cancelar
    description="Plano Premium",
    language="PT",                       # PT, EN, ES, FR
    customer=Customer(email="cliente@email.com"),
)

print(f"Transaction: {payment.transaction_id}")
print(f"URL:         {payment.payment_url}")

# Redirecionar o cliente para payment.payment_url
# Ex. em FastAPI: return RedirectResponse(payment.payment_url)
# Ex. em Django:  return redirect(payment.payment_url)

# Cartão de teste (sandbox):
#   Número: 4018 8100 0015 0015
#   Validade: qualquer data futura
#   CVV: 0101 (sucesso) ou 3333 (falha)
