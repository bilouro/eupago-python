# Verificacao de assinatura

## HMAC-SHA256

A eupago assina cada webhook v2.0 com HMAC-SHA256. O header `X-Signature` contem o hash hexadecimal do body, calculado com o teu webhook secret.

### Como funciona

```
HMAC-SHA256(webhook_secret, request_body) == X-Signature header
```

### Verificacao automatica com o SDK

Quando passas `webhook_secret` a `parse_webhook()`, a verificacao e automatica:

```python
from eupago.webhooks import parse_webhook
from eupago.exceptions import SignatureError

try:
    event = parse_webhook(
        body=request.body,
        headers=dict(request.headers),
        webhook_secret="o-teu-secret",
    )
except SignatureError:
    # Assinatura invalida — rejeitar o pedido
    return Response(status_code=403)
```

Se a assinatura nao corresponder, o SDK lanca `SignatureError`.

### Verificacao manual

Se precisares de verificar manualmente (sem o SDK):

```python
import hashlib
import hmac

def verify_eupago_signature(body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

# Uso
body = request.body  # bytes
signature = request.headers["X-Signature"]
secret = "o-teu-webhook-secret"

if not verify_eupago_signature(body, signature, secret):
    raise ValueError("Assinatura invalida!")
```

!!! danger "Usa compare_digest"
    Nunca uses `==` para comparar hashes — e vulneravel a timing attacks. Usa sempre `hmac.compare_digest()`.

---

## Encriptacao AES-256-CBC

Opcionalmente, a eupago pode encriptar o body do webhook com AES-256-CBC. Nesse caso, o body contem um campo `data` com o payload encriptado em Base64, e o header `X-Initialization-Vector` contem o IV.

### Requisitos

A encriptacao requer o pacote `cryptography`:

```bash
pip install cryptography
```

Ou instalar o SDK com o extra:

```bash
pip install eupago[crypto]
```

### Desencriptacao automatica com o SDK

O SDK detecta e desencripta automaticamente quando:

1. O body contem um campo `data`
2. O header `X-Initialization-Vector` esta presente
3. Passaste `webhook_secret` a `parse_webhook()`

```python
from eupago.webhooks import parse_webhook
from eupago.exceptions import DecryptionError

try:
    event = parse_webhook(
        body=request.body,
        headers=dict(request.headers),
        webhook_secret="o-teu-secret",
    )
    # event ja contem os dados desencriptados
except DecryptionError as e:
    print(f"Falha na desencriptacao: {e}")
```

### Desencriptacao manual

Se precisares de desencriptar manualmente:

```python
import base64
import hashlib
import json

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7


def decrypt_eupago_payload(
    encrypted_data: str,
    secret: str,
    iv_b64: str,
) -> dict:
    iv = base64.b64decode(iv_b64)
    data = base64.b64decode(encrypted_data)
    key = hashlib.sha256(secret.encode()).digest()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(data) + decryptor.finalize()

    unpadder = PKCS7(128).unpadder()
    result = unpadder.update(padded) + unpadder.finalize()

    return json.loads(result)


# Uso
body = json.loads(request.body)
iv = request.headers["X-Initialization-Vector"]
secret = "o-teu-webhook-secret"

payload = decrypt_eupago_payload(body["data"], secret, iv)
print(payload["transactions"]["identifier"])
```

### Como a chave e derivada

A eupago usa SHA-256 do teu webhook secret como chave AES de 256 bits:

```
AES_key = SHA-256(webhook_secret)    # 32 bytes
```

O IV (Initialization Vector) e gerado aleatoriamente por cada webhook e enviado no header `X-Initialization-Vector` em Base64.

---

## Boas praticas de seguranca

### 1. Verifica sempre a assinatura

Nunca processes um webhook sem verificar a assinatura HMAC. Sem verificacao, qualquer pessoa pode enviar webhooks falsos ao teu servidor.

```python
# CORRECTO — verifica a assinatura
event = parse_webhook(body=body, headers=headers, webhook_secret=secret)

# ERRADO — aceita qualquer webhook
event = parse_webhook(body=body, headers=headers)
```

### 2. Guarda o secret de forma segura

```python
import os

# CORRECTO — variavel de ambiente
WEBHOOK_SECRET = os.environ["EUPAGO_WEBHOOK_SECRET"]

# ERRADO — hardcoded no codigo
WEBHOOK_SECRET = "abc123"
```

### 3. Usa HTTPS

Em producao, o teu endpoint de webhook deve usar HTTPS. Em desenvolvimento, usa [ngrok](https://ngrok.com/) ou similar.

### 4. Responde com 200 rapidamente

Processa o webhook de forma assincrona (ex: fila de tarefas) e responde com 200 o mais rapido possivel. Se demorares mais de 30 segundos, a eupago considera que o webhook falhou.

### 5. Idempotencia

A eupago pode reenviar o mesmo webhook multiplas vezes. O teu handler deve ser idempotente — verifica se ja processaste o `transaction_id` antes de actualizar a encomenda.

```python
event = parse_webhook(body=body, headers=headers, webhook_secret=secret)

# Verificar se ja foi processado
if db.webhooks.exists(transaction_id=event.transaction_id):
    return Response(status_code=200)  # Ja processado, retorna 200

# Processar
db.orders.update(order_id=event.order_id, status="paid")
db.webhooks.insert(transaction_id=event.transaction_id)
```

### 6. Nao confies apenas no webhook

Para pagamentos de alto valor, verifica o estado directamente via API alem do webhook:

```python
# Webhook recebido — confirmar via API
status = client.mbway.get_status(transaction_id=event.transaction_id)
if status.status == PaymentStatus.PAID:
    # Pagamento confirmado
    ...
```
