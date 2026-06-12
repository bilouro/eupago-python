# Guia de segurança

O que importa de verdade, em segurança, quando recebes pagamentos pela
eupago com este SDK. Pouca teoria, muito foco nos erros específicos que
custam dinheiro.

## Dados de cartão: não os tens — que continue assim

Com a eupago, o form do cartão, o desafio 3-D Secure e as sheets do
Apple Pay / Google Pay são todos **hospedados pela eupago** (ou pelas
redes de cartões). O PAN nunca toca no teu servidor — e é isso que
mantém a tua exposição PCI DSS em território **SAQ A**, a
auto-avaliação mais leve que existe.

O corolário: **nunca faças proxy nem reimplementes o form do cartão**
para o checkout ficar "seamless". No momento em que números de cartão
passam pelo teu backend, herdas o fardo PCI completo. Redirecciona para
o `payment_url`, deixa a eupago trabalhar, espera pelo webhook.

A mesma lógica vale para a tua base de dados: não existe esquema em que
guardar números de cartão seja a decisão certa. (A recipe
[Persistir pagamentos](recipes/persisting-payments.md) guarda ids,
valores e estados — nada com forma de cartão.)

## Conhece as tuas credenciais e o raio de explosão de cada uma

Tens até três segredos. Destrancam portas diferentes:

| Credencial | Destranca | Se vazar |
|---|---|---|
| **API key** (`api_key`) | Criar pagamentos num canal | O atacante cria pedidos de pagamento lixo em teu nome — chato, não directamente lucrativo |
| **Par OAuth** (`client_id` / `client_secret`) | A Management API inteira: **reembolsos**, listagem de transações, edição/revogação de subscrições — em **todos** os teus canais | O atacante reembolsa o teu dinheiro para wallets que controla. É a jóia da coroa |
| **Chave de webhook** ("Chave Criptográfica") | Verificar/decifrar webhooks (HMAC + AES-256-CBC) | O atacante forja webhooks que passam na verificação → eventos "Paid" falsos |

Regras práticas:

- Os três vivem em **variáveis de ambiente ou num secrets manager** —
  nunca no código, nunca na base de dados, nunca no repo. O SDK lê-os
  na construção do client; mais nada precisa deles.
- O par OAuth **expira ao fim de 1 ano** e pode ser revogado
  instantaneamente no backoffice (*A Minha Conta → Credenciais*). Põe a
  rotação no calendário; não descubras a expiração em produção.
- A chave de webhook roda-se no painel *Webhooks 2.0* do canal. Se
  suspeitares de fuga, roda-a primeiro — é a mais barata de rodar.
- Sandbox e produção são mundos separados. Nunca deixes uma chave de
  produção entrar num `.env.example`, num log de CI ou no histórico de
  shell de um portátil.

## O endpoint de webhook é a tua superfície de ataque

Qualquer um que descubra o URL do teu webhook pode fazer POST para lá.
O ataque clássico é exactamente tão básico quanto parece: enviar
`{"status": "Paid"}` e esperar que a loja envie a mercadoria. A defesa
é em camadas, e o SDK faz a parte difícil:

1. **Verificar antes de parsear.** O `client.webhooks.parse()` valida a
   assinatura HMAC (e decifra, nos canais encriptados) antes de devolver
   o que quer que seja. Um payload que falha lança
   `WebhookSignatureError` — trata-o como hostil: loga (redigido), põe
   em quarentena, não mudes nada.
2. **Idempotência.** A eupago pode re-entregar. Faz hash do body cru e
   torna a segunda entrega um no-op (ver o
   [`on_webhook()` da recipe](recipes/persisting-payments.md)).
3. **Verificar o dinheiro.** Assinatura válida ≠ negócio válido.
   Confirma que o valor e a moeda do webhook batem com o que guardaste
   ao criar o pagamento, e *só depois* fulfilla.
4. **HTTPS sempre**, obviamente — o body do webhook tem PII de clientes.

Ver [Verificação de assinatura](webhooks/signature.md) para os detalhes
ao nível do wire sobre o que é assinado e como.

## O redirect não é um recibo

O `success_url` é para onde mandas o *browser* do cliente depois de um
fluxo hospedado. Não prova nada:

- O cliente pode guardá-lo nos bookmarks e revisitá-lo.
- Um atacante pode navegar directamente para lá sem pagar.
- O pagamento ainda pode falhar *depois* do redirect (edge cases 3DS).

Mostra lá algo simpático ("estamos a confirmar o teu pagamento…"), mas
os **únicos** eventos que viram uma encomenda para paga são um webhook
com assinatura verificada ou um poll autenticado à API da eupago. Nunca
faças `fulfil_order()` a partir de um GET no `success_url`.

## PII: redige em todas as fronteiras

Os payloads de webhook e algumas respostas da API trazem telefones,
emails e nomes. Há duas fronteiras a defender:

- **Logs.** O logger do próprio SDK (`eupago`) redige automaticamente
  padrões de telefone, email e NIF — essa protecção vem de fábrica (e é
  por isso que não deves logar payloads da eupago pelo teu próprio
  logger "por conveniência").
- **Armazenamento.** Se persistes payloads brutos para auditoria,
  redige-os à entrada com o helper público:

```python
from eupago.utils import redact_pii

guardado = redact_pii(webhook_payload)
# {"customer": {"email": "***EMAIL***", "phone": "***PHONE***"}, ...}
```

Combina redação com **retenção**: payloads brutos devem ter prazo de
validade (uma coluna `purge_after`, ou TTL no DynamoDB). Os factos
financeiros — valores, estados, ids de transação — não são PII e podem
viver para sempre; os payloads à volta deles não precisam. Esta
combinação (dados mínimos, payloads redigidos, retenção limitada) é a
maior parte da tua história RGPD para a tabela de pagamentos.

## Torna o histórico à prova de adulteração

O teu **event log** de pagamentos é o que vais buscar numa disputa. Só
é confiável se não puder ser editado em silêncio:

- O role de BD da aplicação recebe `INSERT` mas **não** `UPDATE`/`DELETE`
  na tabela de eventos (ou o equivalente IAM no DynamoDB).
- Pagamentos cancelados/falhados são um *status*, não uma linha apagada.
- Backups encriptados e genuinamente restauráveis — testa uma vez.

## Identificadores vazam mais do que pensas

- Gera o `order_id` a partir de um UUID, não de uma sequência. Ele
  aparece em URLs, webhooks e emails; `ORD-000042` conta ao mundo o teu
  volume de vendas e convida à enumeração dos teus endpoints.
- Trata o `payment_url` como uma capability: quem tem o link vê o valor
  e (no Pay By Link) pode pagá-lo. Não o logues, não o deixes indexar.

## Checklist

- [ ] Form de cartão / wallet sheets: hospedados pela eupago, nunca proxied
- [ ] Segredos em env/secrets manager; rotação OAuth no calendário (1 ano)
- [ ] Handler de webhook: verificar → quarentena em falha → dedup →
      check de valor → transição
- [ ] `success_url` mostra página "a confirmar…"; fulfilment só via
      webhook/poll
- [ ] Payloads brutos guardados via `redact_pii()` + retenção limitada
- [ ] Event log append-only por grant/policy
- [ ] `order_id` não-sequencial
