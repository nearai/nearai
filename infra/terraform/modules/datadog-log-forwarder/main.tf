resource "aws_secretsmanager_secret" "dd_api_key" {
  name        = "${var.environment}-datadog-integration-api-key"
  description = "Encrypted Datadog API Key"
}

resource "aws_secretsmanager_secret_version" "dd_api_key" {
  secret_id     = aws_secretsmanager_secret.dd_api_key.id
  secret_string = "initial-secret"
  
#   lifecycle {
#     ignore_changes = [secret_string]
#   }
}

resource "aws_cloudformation_stack" "datadog_forwarder" {
  name         = "datadog-forwarder"
  capabilities = ["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"]
  parameters   = {
    DdApiKeySecretArn  = aws_secretsmanager_secret.dd_api_key.arn
    DdSite             = "us3.datadoghq.com"
    FunctionName       = "${var.environment}-datadog-forwarder"
  }
  template_url = "https://datadog-cloudformation-template.s3.amazonaws.com/aws/forwarder/latest.yaml"
}