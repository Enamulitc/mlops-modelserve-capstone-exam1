resource "aws_ecr_repository" "this" {
  name = "modelserve/proddetection"
  tags = var.tags
}
