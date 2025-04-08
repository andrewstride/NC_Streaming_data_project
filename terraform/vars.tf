variable "aws_region" {
  type = string
}

variable "aws_account" {
  type = string
}

variable "lambda_name" {
  type = string
}

variable "guardian_api_key" {
  type = string
  sensitive = true
}

variable "sqs_queue_name" {
  type = string
}