variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket EC2 should access"
  type        = string
}

variable "tags" {
  description = "Common tags to apply"
  type        = map(string)
  default     = {}
}
