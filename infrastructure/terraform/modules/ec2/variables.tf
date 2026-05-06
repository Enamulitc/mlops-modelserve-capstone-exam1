variable "subnet_id" { type = string }
variable "sg_id"     { type = string }
variable "instance_type" {
  type    = string
  # Use a default with at least 4 vCPU and >= 8 GiB RAM. t3.xlarge has 4 vCPU and 16 GiB RAM.
  default = "t3.xlarge"
}
variable "tags" { type = map(string) }

variable "public_key_path" {
  description = "Absolute path to the SSH public key file (.pub) to register as an AWS key pair"
  type        = string
}

variable "iam_instance_profile" {
  description = "IAM instance profile name to attach to EC2"
  type        = string
}