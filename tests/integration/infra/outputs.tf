output "webhook_url" {
  description = "Configure this URL in the eupago sandbox channel (Webhooks 2.0)."
  value       = "${trimsuffix(aws_apigatewayv2_stage.default.invoke_url, "/")}/webhook"
}

output "table_name" {
  description = "DynamoDB table — pass as EUPAGO_WEBHOOK_TABLE to the integration test."
  value       = aws_dynamodb_table.captures.name
}
