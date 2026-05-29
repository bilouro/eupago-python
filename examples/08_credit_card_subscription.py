"""
Cartão de Crédito — Subscrição (cobrança recorrente).

Primeiro o cliente regista o cartão (uma única vez, com 3DS).
Depois, podes cobrar quantas vezes precisares sem ele intervir.

Fluxo:
  App → create_subscription → Cliente regista cartão na página eupago
  → Recebes recurrent_id por webhook ou na consulta de transações
  → App → charge_subscription(recurrent_id, amount) — cobra silenciosamente
"""

from decimal import Decimal

from eupago import EupagoClient
from eupago.models import Customer

client = EupagoClient(api_key="xxxx-xxxx-xxxx-xxxx-xxxx", sandbox=True)

# Passo 1 — Registar o cartão para uso recorrente
subscription = client.credit_card.create_subscription(
    order_id="SUB-2026-001",
    amount=Decimal("0.00"),  # 0 = só registo; >0 = primeiro pagamento + registo
    success_url="https://a-tua-loja.pt/sub/ok",
    error_url="https://a-tua-loja.pt/sub/erro",
    back_url="https://a-tua-loja.pt/conta",
    customer=Customer(email="cliente@email.com", notify=True),
)

print(f"Redirect URL: {subscription.payment_url}")  # cliente regista cartão aqui
# Após sucesso, recebes o recurrent_id no webhook (campo do raw payload)

# Passo 2 — Cobrar mensalmente (chamada de servidor, sem intervenção do cliente)
recurrent_id = 12345  # vindo do webhook do passo 1

charge = client.credit_card.charge_subscription(
    recurrent_id=recurrent_id,
    order_id="SUB-2026-001-M01",
    amount=Decimal("19.90"),  # mensalidade
)
print(f"Cobrança: {charge.status} ({charge.transaction_id})")


# --- Reembolso de uma cobrança específica ---
#
# refund = client.refunds.refund(
#     transaction_id=charge.transaction_id,
#     value=Decimal("19.90"),
# )
