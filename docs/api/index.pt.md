# Referencia API

Documentacao gerada automaticamente a partir do codigo-fonte.

## Client

::: eupago.EupagoClient
    options:
      show_source: false
      show_root_heading: true
      heading_level: 3
      members_order: source

## Modelos

### PaymentResult

::: eupago.models.PaymentResult
    options:
      show_source: false
      show_root_heading: true
      heading_level: 4
      members_order: source

### PaymentStatus

::: eupago.models.PaymentStatus
    options:
      show_source: false
      show_root_heading: true
      heading_level: 4
      members_order: source

### Customer

::: eupago.models.Customer
    options:
      show_source: false
      show_root_heading: true
      heading_level: 4
      members_order: source

### WebhookEvent

::: eupago.models.WebhookEvent
    options:
      show_source: false
      show_root_heading: true
      heading_level: 4
      members_order: source

## Excepcoes

::: eupago.exceptions
    options:
      show_source: false
      show_root_heading: true
      heading_level: 3
      members_order: source

## Serviços

Cada serviço é acedido via uma propriedade no client (`client.mbway`,
`client.multibanco`, …). Não os importas nem instancias directamente.

### MBWayService

::: eupago.services.MBWayService
    options:
      show_source: false
      show_root_heading: true
      heading_level: 4
      members_order: source

### MultibancoService

::: eupago.services.MultibancoService
    options:
      show_source: false
      show_root_heading: true
      heading_level: 4
      members_order: source

### CreditCardService

::: eupago.services.CreditCardService
    options:
      show_source: false
      show_root_heading: true
      heading_level: 4
      members_order: source

### ApplePayService

::: eupago.services.ApplePayService
    options:
      show_source: false
      show_root_heading: true
      heading_level: 4
      members_order: source

### GooglePayService

::: eupago.services.GooglePayService
    options:
      show_source: false
      show_root_heading: true
      heading_level: 4
      members_order: source

### PayByLinkService

::: eupago.services.PayByLinkService
    options:
      show_source: false
      show_root_heading: true
      heading_level: 4
      members_order: source

### RefundService

::: eupago.services.RefundService
    options:
      show_source: false
      show_root_heading: true
      heading_level: 4
      members_order: source

## Webhooks

### parse_webhook

::: eupago.webhooks.parse_webhook
    options:
      show_source: false
      show_root_heading: true
      heading_level: 4
      members_order: source
