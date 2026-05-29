variable "region" {
  description = "AWS region to deploy the test webhook receiver into."
  type        = string
  default     = "eu-west-1"
}

variable "name_prefix" {
  description = "Prefix for all created resources."
  type        = string
  default     = "eupago-webhook-test"
}

variable "ttl_days" {
  description = "Days after which captured webhook items auto-expire from DynamoDB."
  type        = number
  default     = 7
}

variable "webhook_secret" {
  description = <<-EOT
    The channel's "Chave Criptográfica". Optional: required only for the Lambda
    to decrypt encrypted webhooks and key captures by ``order_id`` (otherwise
    encrypted captures land as ``raw-<uuid>``). Pass via -var, TF_VAR_webhook_secret,
    or a gitignored *.tfvars file. Never commit this value.
  EOT
  type        = string
  default     = ""
  sensitive   = true
}
