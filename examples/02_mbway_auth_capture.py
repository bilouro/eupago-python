"""
MB WAY — Auth + Capture (reservar e cobrar depois).

Útil quando queres reservar o montante primeiro (ex: reserva de hotel)
e cobrar depois quando o serviço é prestado.

Fluxo:
  App → authorize → Cliente aprova → App → capture → Pago
"""

from decimal import Decimal

from eupago import EupagoClient

client = EupagoClient(api_key="xxxx-xxxx-xxxx-xxxx-xxxx", sandbox=True)

# Passo 1: Autorizar — reserva o montante no tlm do cliente
auth = client.mbway.authorize(
    order_id="RESERVA-001",
    amount=Decimal("120.00"),
    phone_number="912345678",
)

print(f"Autorização: {auth.transaction_id}")
print(f"Status:      {auth.status}")  # PENDING — aguardar aprovação

# Passo 2: Capturar — cobrar o montante autorizado
#   (só depois do cliente aprovar no telemóvel)
captured = client.mbway.capture(
    transaction_id=auth.transaction_id,
    amount=Decimal("120.00"),
)

print(f"Captura: {captured.status}")  # PAID


# --- Reembolso ---
#
# refund = client.refunds.refund(
#     transaction_id=captured.transaction_id,
#     value=Decimal("120.00"),
# )
