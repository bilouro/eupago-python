terraform {
  required_version = ">= 1.5"
  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 5.0" }
    archive = { source = "hashicorp/archive", version = "~> 2.4" }
    null    = { source = "hashicorp/null", version = "~> 3.2" }
  }
}

# Credentials/account come from the standard AWS chain (env vars / AWS_PROFILE).
# Nothing here is tied to a specific account.
provider "aws" {
  region = var.region
}

resource "null_resource" "build_lambda_package" {
  triggers = {
    handler      = filemd5("${path.module}/handler.py")
    requirements = filemd5("${path.module}/requirements.txt")
    build_script = filemd5("${path.module}/build.sh")
  }
  provisioner "local-exec" {
    command = "${path.module}/build.sh ${path.module}"
  }
}

data "archive_file" "fn" {
  type        = "zip"
  source_dir  = "${path.module}/.build/package"
  output_path = "${path.module}/.build/fn.zip"
  depends_on  = [null_resource.build_lambda_package]
}

resource "aws_dynamodb_table" "captures" {
  name         = "${var.name_prefix}-captures"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "order_id"

  attribute {
    name = "order_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

resource "aws_iam_role" "lambda" {
  name = "${var.name_prefix}-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "ddb_put" {
  name = "ddb-put"
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:PutItem"]
      Resource = aws_dynamodb_table.captures.arn
    }]
  })
}

resource "aws_lambda_function" "receiver" {
  function_name    = "${var.name_prefix}-fn"
  runtime          = "python3.12"
  handler          = "handler.handler"
  filename         = data.archive_file.fn.output_path
  source_code_hash = data.archive_file.fn.output_base64sha256
  role             = aws_iam_role.lambda.arn
  timeout          = 10

  environment {
    variables = merge(
      {
        WEBHOOK_TABLE    = aws_dynamodb_table.captures.name
        WEBHOOK_TTL_DAYS = tostring(var.ttl_days)
      },
      var.webhook_secret != "" ? { WEBHOOK_SECRET = var.webhook_secret } : {},
    )
  }
}

resource "aws_apigatewayv2_api" "api" {
  name          = "${var.name_prefix}-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.receiver.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "post_webhook" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "POST /webhook"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.receiver.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}
