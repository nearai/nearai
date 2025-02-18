terraform {
  backend "s3" {
    bucket = "nearai-terraform-state"
    key    = "production/terraform.tfstate"
    region = "us-west-2"
  }
}

module "datadog-log-forwarder" {
  source = "../../modules/datadog-log-forwarder"
  environment = local.environment
  aws_region = local.aws_region
  cloudwatch_log_groups = {
    "production-agent-runner-base" = "/aws/lambda/production-agent-runner-base"
    "production-agent-runner-agentkit"    = "/aws/lambda/production-agent-runner-agentkit"
    "production-agent-runner-web-agent" = "/aws/lambda/production-agent-runner-web-agent"
    "production-agent-runner-langgraph-0-1-4" = "/aws/lambda/production-agent-runner-langgraph-0-1-4"
    "production-agent-runner-langgraph-0-2-26" = "/aws/lambda/production-agent-runner-langgraph-0-2-26"
    "production-agent-runner-masa" = "/aws/lambda/production-agent-runner-masa"
    "production-agent-runner-ts" = "/aws/lambda/production-agent-runner-ts"
  }
}
