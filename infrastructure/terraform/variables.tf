variable "region" {
  type    = string
  default = "ap-southeast-1"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "tags" {
  type    = map(string)
  default = { Project = "modelserve" }
}

variable "public_key_path" {
  description = "Path to the public key file for EC2 instances"
  type        = string
  default     = "/Users/enam.devopsgmail.com/.ssh/mlops-key.pub"
}
