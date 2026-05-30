"""
Cartão de Crédito — Subscrição (cobrança recorrente).

Passo 1 — o cliente regista o cartão uma única vez (com 3DS).
Passo 2 — cobras quantas vezes precisares, sem ele intervir.

Fluxo:
  App  -> create_subscription (com bloco subscription obrigatório)
       -> redirectUrl ".../formsub/<id>"
       -> Cliente regista o cartão na página alojada da eupago
       -> Recebes o webhook de registo com o subscription_id (= subscriptionID)
       -> App -> charge_subscription(recurrent_id=subscription_id, ...) silenciosamente

⚠️ Esta funcionalidade requer que o canal eupago tenha "Cartão de Crédito —
Subscrição" provisionado. Não está no canal demo por defeito — abre ticket
em suporte@eupago.pt se precisares.
"""

from decimal import Decimal

from eupago import EupagoClient
from eupago.models import Customer

client = EupagoClient(api_key="xxxx-xxxx-xxxx-xxxx-xxxx", sandbox=True)

# Passo 1 — Registar o cartão para uso recorrente
# As três return URLs são obrigatórias; o bloco "subscription" é adicionado
# automaticamente pelo SDK com defaults sensatos (mensal, dia 1, 1 ano).
subscription = client.credit_card.create_subscription(
    order_id="SUB-2026-001",
    amount=Decimal("19.90"),
    success_url="https://a-tua-loja.pt/sub/ok",
    error_url="https://a-tua-loja.pt/sub/erro",
    back_url="https://a-tua-loja.pt/conta",
    customer=Customer(email="cliente@email.com", notify=True),
    # Opcionais — defaults equivalem a uma subscrição mensal de 1 ano:
    # periodicity="Mensal",
    # collection_day=1,
    # auto_process=False,                     # True = eupago cobra sozinho
    # start_date=date(2026, 6, 1),
    # limit_date=date(2027, 6, 1),
)

print(f"Redirect URL:    {subscription.payment_url}")  # cliente regista cartão aqui
# subscription.transaction_id = subscriptionID (hex de 32 chars) — guarda para cobrar depois
subscription_id = subscription.transaction_id


# Passo 2 — Cobrar mensalmente (chamada de servidor, sem intervenção do cliente)
# Note que os success/error/back URLs são REQUIRED também na cobrança.
charge = client.credit_card.charge_subscription(
    recurrent_id=subscription_id,  # vem do passo 1 (str hex, não int)
    order_id="SUB-2026-001-M01",
    amount=Decimal("19.90"),
    success_url="https://a-tua-loja.pt/sub/ok",
    error_url="https://a-tua-loja.pt/sub/erro",
    back_url="https://a-tua-loja.pt/conta",
    # days_to_capture=7,  # opcional — adia a captura X dias
)
print(f"Cobrança: {charge.status} ({charge.transaction_id})")


# --- Reembolso de uma cobrança específica ---
#
# refund = client.refunds.refund(
#     transaction_id=charge.transaction_id,
#     value=Decimal("19.90"),
# )
