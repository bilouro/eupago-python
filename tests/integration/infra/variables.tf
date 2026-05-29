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
