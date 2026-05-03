terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.3.0"
}

provider "aws" {
  region = var.region
}

module "vpc" {
  source = "./modules/vpc"
  cidr   = var.vpc_cidr
  tags   = var.tags
}

module "s3" {
  source = "./modules/s3"
  tags   = var.tags
}

module "ecr" {
  source = "./modules/ecr"
  tags   = var.tags
}

module "iam" {
  source        = "./modules/iam"
  s3_bucket_arn = module.s3.bucket_arn
  tags          = var.tags
}

module "security" {
  source = "./modules/security"
  vpc_id = module.vpc.vpc_id
  tags   = var.tags
}

module "ec2" {
  source          = "./modules/ec2"
  subnet_id       = module.vpc.public_subnet_id
  sg_id           = module.security.sg_id
  public_key_path = var.public_key_path
  iam_instance_profile = module.iam.instance_profile_name
  tags            = var.tags
}
