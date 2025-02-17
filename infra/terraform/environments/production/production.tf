terraform {
  backend "s3" {
    bucket = "nearai-terraform-state"
    key    = "production/terraform.tfstate"
    region = "us-west-2"
  }
}

locals {
  environment = "prod"
  aws_region = "us-west-2"
}

module "datadog-log-forwarder" {
  source = "../../modules/datadog-log-forwarder"
  environment = local.environment
  aws_region = local.aws_region
}

