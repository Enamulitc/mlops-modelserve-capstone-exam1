variable "subnet_id" { type = string }
variable "sg_id"     { type = string }
variable "instance_type" {
  type    = string
  default = "t3.small"
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