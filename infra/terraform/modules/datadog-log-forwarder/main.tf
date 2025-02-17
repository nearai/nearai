resource "aws_secretsmanager_secret" "dd_api_key" {
  name        = "${var.environment}-datadog-integration-api-key"
  description = "Encrypted Datadog API Key"
}

resource "aws_secretsmanager_secret_version" "dd_api_key" {
  secret_id     = aws_secretsmanager_secret.dd_api_key.id
  secret_string = "initial-secret"
  
  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_cloudformation_stack" "datadog_forwarder" {
  name         = "datadog-forwarder"
  capabilities = ["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"]
  parameters   = {
    DdApiKeySecretArn  = aws_secretsmanager_secret.dd_api_key.arn
    DdSite             = "us3.datadoghq.com"
    FunctionName       = "${var.environment}-datadog-forwarder"
    DdTags             = "env:${var.environment}"
    DdForwardLog       = "true"
  }
  template_url = "https://datadog-cloudformation-template.s3.amazonaws.com/aws/forwarder/latest.yaml"
}



# Create CloudWatch Log subscription for the forwarder
resource "aws_cloudwatch_log_subscription_filter" "datadog_log_forward" {
  for_each        = var.cloudwatch_log_groups
  name            = "datadog-log-${each.key}"
  log_group_name  = each.value
  filter_pattern  = ""  # Empty pattern means all logs
  destination_arn = aws_cloudformation_stack.datadog_forwarder.outputs.DatadogForwarderArn
}