resource "aws_iam_role" "ec2_workload" {
  name               = "modelserve-ec2-workload-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
  tags               = var.tags
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "modelserve-ec2-instance-profile"
  role = aws_iam_role.ec2_workload.name
}

resource "aws_iam_role_policy" "ec2_s3_ecr_access" {
  name   = "modelserve-ec2-s3-ecr-access"
  role   = aws_iam_role.ec2_workload.id
  policy = data.aws_iam_policy_document.ec2_s3_ecr_access.json
}

data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "ec2_s3_ecr_access" {
  statement {
    sid = "S3BucketAccess"
    actions = [
      "s3:ListBucket",
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject"
    ]
    resources = [
      var.s3_bucket_arn,
      "${var.s3_bucket_arn}/*"
    ]
  }

  statement {
    sid = "EcrReadAccess"
    actions = [
      "ecr:GetAuthorizationToken",
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage"
    ]
    resources = ["*"]
  }
}