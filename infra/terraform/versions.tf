terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Compute/cloud provider: AWS (decision recorded 2026-07-30; see CLAUDE.md and
# docs/EXECUTION_PLAN.md §6 step 8). Provider block only — no resources yet.
# Region and account wiring are a separate, later decision.
provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region for LandVault infrastructure."
  type        = string
  default     = "eu-west-2"
}
