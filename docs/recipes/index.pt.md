# Receitas

Guias completos de integracao com frameworks Python populares. Cada receita inclui:

- Criacao de pagamento
- Handler de webhook (v2.0 POST + v1.0 GET)
- Boas praticas de seguranca

## Arquitectura

<div class="grid cards" markdown>

-   :material-database:{ .lg .middle } **Persistir pagamentos**

    ---

    O esquema de referência e a máquina de estados para guardar
    pagamentos: write-ahead, webhooks idempotentes, linkagem de
    reembolsos e as armadilhas do Pay By Link — PostgreSQL + DynamoDB.

    [:octicons-arrow-right-24: Persistir pagamentos](persisting-payments.md)

</div>

## Frameworks disponiveis

<div class="grid cards" markdown>

-   :material-lightning-bolt:{ .lg .middle } **FastAPI**

    ---

    Integracao async-first com FastAPI

    [:octicons-arrow-right-24: FastAPI](fastapi.md)

-   :material-language-python:{ .lg .middle } **Django**

    ---

    Integracao com Django views e urls.py

    [:octicons-arrow-right-24: Django](django.md)

-   :material-flask:{ .lg .middle } **Flask**

    ---

    Integracao com Flask routes

    [:octicons-arrow-right-24: Flask](flask.md)

</div>

## Qual framework escolher?

| Criterio | FastAPI | Django | Flask |
|---|---|---|---|
| Async nativo | Sim | Parcial (ASGI) | Nao (usa gevent/etc.) |
| Baterias incluidas | Nao | Sim (ORM, admin, auth) | Nao |
| Curva de aprendizagem | Baixa | Media | Baixa |
| Ideal para | APIs, microservicos | Apps full-stack | Prototipos, APIs simples |

!!! tip "Sem framework?"
    O SDK funciona sem framework — so precisas de Python. Os exemplos usam frameworks apenas para o endpoint HTTP que recebe webhooks.
