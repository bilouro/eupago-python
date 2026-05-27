"""
Cartão de Crédito — Subscriptions (pagamentos recorrentes).

Regista o cartão do cliente uma vez. Depois podes cobrar mensalidades
sem o cliente repetir os dados do cartão (MIT - Merchant Initiated Transaction).

Fluxo:
  1. create_subscription → Cliente regista cartão (uma vez)
  2. charge_subscription → Cobrar mensalidade (recorrente, sem interação)
"""

from decimal import Decimal

from eupago import EupagoClient
from eupago.models import Customer

client = EupagoClient(api_key="xxxx-xxxx-xxxx-xxxx-xxxx", sandbox=True)


# --- Passo 1: Registar o cartão (uma vez) ---

sub = client.credit_card.create_subscription(
    order_id="SUB-PREMIUM-001",
    amount=Decimal("29.99"),             # Primeiro pagamento
    success_url="https://loja.pt/subscricao/ok",
    error_url="https://loja.pt/subscricao/erro",
    customer=Customer(email="assinante@email.com"),
)

print(f"URL de registo: {sub.payment_url}")
# Redirecionar o cliente para sub.payment_url
# O cliente preenche os dados do cartão.
# No backoffice eupago, obtens o recurrent_id.


# --- Passo 2: Cobrar mensalidade (sem interação do cliente) ---

# O recurrent_id vem do backoffice eupago após o cliente registar o cartão.
recurrent_id = 42  # Exemplo

charge = client.credit_card.charge_subscription(
    recurrent_id=recurrent_id,
    order_id="MENSALIDADE-2026-06",
    amount=Decimal("29.99"),
    customer=Customer(email="assinante@email.com"),
)

print(f"Cobrança: {charge.transaction_id}")
print(f"Status:   {charge.status}")

# Repetir charge_subscription todos os meses para cobrar automaticamente.
