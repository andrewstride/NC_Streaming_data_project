terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket = "andrewstride-nc-data-streaming-tf-state"
    key = "terraform.tfstate"
    region = "eu-west-2"
  }
}

# Configure the AWS Provider
provider "aws" {
  region = var.aws_region
}

