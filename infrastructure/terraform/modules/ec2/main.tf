data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "aws_key_pair" "this" {
  key_name   = "mlops-key"
  public_key = file(var.public_key_path)
}

resource "aws_instance" "this" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = [var.sg_id]
  associate_public_ip_address = true
  key_name                    = aws_key_pair.this.key_name
  iam_instance_profile        = var.iam_instance_profile
  # Root EBS volume: 100 GiB gp3 to meet storage requirement
  root_block_device {
    volume_size = 100
    volume_type = "gp3"
  }

  tags                        = var.tags
}