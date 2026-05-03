resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "this" {
  bucket = "modelserve-artifacts-${random_id.suffix.hex}"
  tags   = var.tags
}
