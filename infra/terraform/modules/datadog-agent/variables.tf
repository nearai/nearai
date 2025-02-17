variable "vpc_id" {
  description = "VPC ID where the Datadog agent will be deployed"
  type        = string
}

variable "instance_count" {
  description = "Number of Datadog agent instances to run"
  type        = number
  default     = 1
}

variable "ecs_cluster_id" {
  description = "ECS Cluster ID where the Datadog agent will be deployed"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "datadog_api_key_secret_arn" {
  description = "ARN of the AWS Secrets Manager secret containing the Datadog API key"
  type        = string
}