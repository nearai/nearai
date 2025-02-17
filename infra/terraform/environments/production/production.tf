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
    "production-agent-runner-agentkit"    = "/aws/lambda/production-agent-runner-agentkit"
    "production-agent-runner-base" = "/aws/lambda/production-agent-runner-base"
    "production-agent-runner-web-agent" = "/aws/lambda/production-agent-runner-web-agent"
  }
}

