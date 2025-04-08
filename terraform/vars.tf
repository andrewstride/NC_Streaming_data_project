variable "aws_region" {
  type = string
}

variable "lambda_name" {
  type = string
}

variable "guardian_api_key" {
  type = string
  sensitive = true
}