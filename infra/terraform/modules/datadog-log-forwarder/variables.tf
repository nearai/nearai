variable "aws_region" {
  description = "AWS region"
  default = "us-east-2"
}

variable "environment" {
  description = "Environment name (e.g., prod, staging, dev)"
  type        = string
}


variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
  default     = "543900120763"
}
