# Webhook receiver — SDK test infrastructure

Self-contained AWS infra the **SDK** owns to test the real eupago webhook flow,
independent of any application. It is **test-only**.

```
eupago  --POST-->  API Gateway (HTTP API)  -->  Lambda  -->  DynamoDB
                    POST /webhook                captures raw   keyed by order_id
                                                 body + headers  (TTL auto-expire)
```

The Lambda only **captures** (raw body + headers). Signature verification and
decryption are validated **offline** by the test, from the captured bytes — so
the receiver stays trivial and dependency-free.

## Prerequisites

- [Terraform](https://developer.hashicorp.com/terraform) ≥ 1.5
- AWS CLI configured with credentials (`export AWS_PROFILE=…`). The Terraform
  uses the standard AWS credential chain — **nothing here is tied to an account**.

## 1. Deploy

```bash
cd tests/integration/infra
terraform init
terraform apply \
    -var region=eu-west-1 \
    -var webhook_secret="$EUPAGO_WEBHOOK_SECRET"   # optional: see note below

# Outputs:
#   webhook_url = https://xxxx.execute-api.<region>.amazonaws.com/webhook
#   table_name  = eupago-webhook-test-captures
```

Cost: pay-per-use (Lambda + HTTP API + on-demand DynamoDB) — effectively **$0**
at test volume. Captured items auto-expire after `ttl_days` (default 7).

**About `webhook_secret`** — pass the channel's *Chave Criptográfica* to let the
Lambda decrypt encrypted webhooks and key captures by the merchant's `order_id`.
Without it, encrypted captures still land in DynamoDB but keyed as
`raw-<uuid>`. Prefer `TF_VAR_webhook_secret` or a gitignored `*.tfvars` file
over passing it on the command line. The deployment bundles the `cryptography`
wheel (Linux manylinux, py3.12) via `build.sh`.

## 2. Configure eupago

In the eupago **sandbox backoffice**, open the channel → **Webhooks 2.0** and set
the **Webhook Endpoint** to the `webhook_url` output. For the first capture leave
**encryption off**; do a second run with encryption **on** (note the generated
"Chave Criptográfica") to exercise the AES path.

## 3. Capture a real webhook

```bash
export EUPAGO_API_KEY=…                 # sandbox API key
export EUPAGO_WEBHOOK_TABLE=…           # the table_name output
export EUPAGO_WEBHOOK_SECRET=…          # only if encryption is on
pytest -m integration tests/integration/test_webhook_capture.py -s
```

The test creates a Multibanco reference and then waits. Trigger the webhook by
marking that reference **Paga** in the backoffice:

> Operações > Consultar > Transações → locate the reference → Ações → **Marcar como Paga**

The test polls DynamoDB for the capture and validates `parse_webhook`.

## 4. Tear down

```bash
terraform destroy
```

## Security

- `*.tfstate`, `.terraform/` and `*.tfvars` are git-ignored — they contain
  account IDs/ARNs. **Never commit them.**
- The endpoint is public (eupago must reach it); authenticity is enforced by the
  eupago HMAC signature, validated by the SDK, not by AWS auth.
