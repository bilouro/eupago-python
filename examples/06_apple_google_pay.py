"""
Apple Pay e Google Pay — Pagamento com wallet digital.

Endpoints simples: gera um URL, redireciona o cliente, pagamento imediato.
Sem auth/capture, sem subscriptions.

Nota: o webhook (callback_url) é configurado uma vez no backoffice eupago.
      Aqui só passas os URLs de redirect do browser do cliente.
"""

from decimal import Decimal

from eupago import EupagoClient

client = EupagoClient(api_key="xxxx-xxxx-xxxx-xxxx-xxxx", sandbox=True)


# --- Apple Pay ---

apple = client.apple_pay.create_payment(
    order_id="ORD-APPLE-001",
    amount=Decimal("29.99"),
    success_url="https://loja.pt/pagamento/ok",    # Redirect do browser (cliente vê)
    error_url="https://loja.pt/pagamento/erro",     # Redirect do browser (cliente vê)
)

print(f"Apple Pay URL: {apple.payment_url}")
# Redirecionar cliente para apple.payment_url
# Ex. FastAPI: return RedirectResponse(apple.payment_url)
# Ex. Django:  return redirect(apple.payment_url)


# --- Google Pay ---

google = client.google_pay.create_payment(
    order_id="ORD-GOOGLE-001",
    amount=Decimal("35.00"),
    success_url="https://loja.pt/pagamento/ok",
    error_url="https://loja.pt/pagamento/erro",
)

print(f"Google Pay URL: {google.payment_url}")
# Redirecionar cliente para google.payment_url
