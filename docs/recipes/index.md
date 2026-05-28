# Recipes

Complete integration guides for popular Python frameworks. Each recipe includes:

- Payment creation
- Webhook handler (v2.0 POST + v1.0 GET)
- Security best practices

## Available frameworks

<div class="grid cards" markdown>

-   :material-lightning-bolt:{ .lg .middle } **FastAPI**

    ---

    Async-first integration with FastAPI

    [:octicons-arrow-right-24: FastAPI](fastapi.md)

-   :material-language-python:{ .lg .middle } **Django**

    ---

    Integration with Django views and urls.py

    [:octicons-arrow-right-24: Django](django.md)

-   :material-flask:{ .lg .middle } **Flask**

    ---

    Integration with Flask routes

    [:octicons-arrow-right-24: Flask](flask.md)

</div>

## Which framework to choose?

| Criteria | FastAPI | Django | Flask |
|---|---|---|---|
| Native async | Yes | Partial (ASGI) | No (use gevent/etc.) |
| Batteries included | No | Yes (ORM, admin, auth) | No |
| Learning curve | Low | Medium | Low |
| Ideal for | APIs, microservices | Full-stack apps | Prototypes, simple APIs |

!!! tip "No framework?"
    The SDK works without any framework — you only need Python. The examples use frameworks only for the HTTP endpoint that receives webhooks.
