"""
infrastructure/__main__.py — Pulumi Python program
----------------------------------------------------
Provisions the minimum AWS resources required for Option A topology
(everything on a single EC2 instance):

  - VPC + public subnet + internet gateway
  - Security group  (ports 22, 8000, 5000, 3000, 9090)
  - EC2 t3.small instance (with user-data bootstrap script)
  - Elastic IP
  - S3 bucket  (MLflow artifacts + Feast offline store)
  - ECR repository  (Docker images)
  - IAM role + instance profile  (EC2 → S3 + ECR access)

All resources tagged:  Project: modelserve

Stack outputs (used by GitHub Actions deploy job):
  - instance_ip    → public IP of the EC2 instance
  - ecr_repo_url   → ECR repository URL
  - s3_bucket_name → S3 bucket name

Usage (from infrastructure/ directory):
  pulumi stack init dev
  pulumi up --yes
  pulumi destroy --yes
"""

import pulumi
import pulumi_aws as aws
import json

# Pulumi program: provisions a minimal AWS topology suitable for a single-EC2
# deployment of the model serving stack. This is an alternative to the Terraform
# modules (Option A). Pulumi lets you express infra in Python with programmatic
# control flow and dynamic values.

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
config = pulumi.Config()
region          = config.get("region") or "ap-southeast-1"
instance_type   = config.get("instanceType") or "t3.small"
key_pair_name   = config.get("keyPairName") or "modelserve-key"
project_tag     = {"Project": "modelserve"}

# ─────────────────────────────────────────────
# VPC & Networking
# ─────────────────────────────────────────────
# Create a small VPC with a public subnet so the EC2 instance can have a public IP
vpc = aws.ec2.Vpc(
    "modelserve-vpc",
    cidr_block="10.0.0.0/16",
    enable_dns_support=True,
    enable_dns_hostnames=True,
    tags={**project_tag, "Name": "modelserve-vpc"},
)

igw = aws.ec2.InternetGateway(
    "modelserve-igw",
    vpc_id=vpc.id,
    tags={**project_tag, "Name": "modelserve-igw"},
)

public_subnet = aws.ec2.Subnet(
    "modelserve-public-subnet",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    map_public_ip_on_launch=True,
    availability_zone=f"{region}a",
    tags={**project_tag, "Name": "modelserve-public-subnet"},
)

route_table = aws.ec2.RouteTable(
    "modelserve-rt",
    vpc_id=vpc.id,
    routes=[{"cidr_block": "0.0.0.0/0", "gateway_id": igw.id}],
    tags={**project_tag, "Name": "modelserve-rt"},
)

aws.ec2.RouteTableAssociation(
    "modelserve-rta",
    subnet_id=public_subnet.id,
    route_table_id=route_table.id,
)

# ─────────────────────────────────────────────
# Security Group
# ─────────────────────────────────────────────
# Security group opens required ports for the demo: in production narrow SSH
# and other access to trusted IPs only.
sg = aws.ec2.SecurityGroup(
    "modelserve-sg",
    vpc_id=vpc.id,
    description="ModelServe security group",
    ingress=[
        # SSH — restrict to your IP in production!
        {"protocol": "tcp", "from_port": 22,   "to_port": 22,   "cidr_blocks": ["0.0.0.0/0"]},
        # FastAPI inference API
        {"protocol": "tcp", "from_port": 8000, "to_port": 8000, "cidr_blocks": ["0.0.0.0/0"]},
        # MLflow UI
        {"protocol": "tcp", "from_port": 5000, "to_port": 5000, "cidr_blocks": ["0.0.0.0/0"]},
        # Grafana UI
        {"protocol": "tcp", "from_port": 3000, "to_port": 3000, "cidr_blocks": ["0.0.0.0/0"]},
        # Prometheus UI
        {"protocol": "tcp", "from_port": 9090, "to_port": 9090, "cidr_blocks": ["0.0.0.0/0"]},
    ],
    egress=[
        {"protocol": "-1", "from_port": 0, "to_port": 0, "cidr_blocks": ["0.0.0.0/0"]},
    ],
    tags={**project_tag, "Name": "modelserve-sg"},
)

# ─────────────────────────────────────────────
# S3 Bucket (MLflow artifacts + Feast offline)
# ─────────────────────────────────────────────
# Store model artifacts and offline feature data in S3 so multiple components
# (CI/CD, EC2) can access them. Versioning helps with recovery/rollback.
s3_bucket = aws.s3.BucketV2(
    "modelserve-artifacts",
    tags={**project_tag, "Name": "modelserve-artifacts"},
)

aws.s3.BucketVersioningV2(
    "modelserve-artifacts-versioning",
    bucket=s3_bucket.id,
    versioning_configuration={"status": "Enabled"},
)

# ─────────────────────────────────────────────
# ECR Repository
# ─────────────────────────────────────────────
# ECR stores Docker images built by CI and pulled by the EC2 instance.
ecr_repo = aws.ecr.Repository(
    "modelserve-api",
    name="modelserve/proddetection",
    force_delete=True,   # allows pulumi destroy even when images exist
    tags={**project_tag, "Name": "modelserve-api"},
)

# ─────────────────────────────────────────────
# IAM Role for EC2 (S3 + ECR access)
# ─────────────────────────────────────────────
# Instance-role grants the EC2 VM permissions to read model artifacts from S3
# and pull images from ECR without embedding long-lived credentials on the VM.
ec2_role = aws.iam.Role(
    "modelserve-ec2-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }],
    }),
    tags=project_tag,
)

aws.iam.RolePolicyAttachment(
    "modelserve-s3-policy",
    role=ec2_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonS3FullAccess",
)
aws.iam.RolePolicyAttachment(
    "modelserve-ecr-policy",
    role=ec2_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
)

instance_profile = aws.iam.InstanceProfile(
    "modelserve-instance-profile",
    role=ec2_role.name,
    tags=project_tag,
)

# ─────────────────────────────────────────────
# EC2 User-Data bootstrap script
# ─────────────────────────────────────────────
# The EC2 user-data bootstraps the machine: installs docker, clones the repo and
# starts the docker-compose stack. In production consider using an AMI with
# pre-baked images or a more robust deployment pipeline.
user_data = s3_bucket.bucket.apply(lambda bucket: f"""#!/bin/bash
set -e
apt-get update -y
apt-get install -y docker.io docker-compose-plugin git curl

# Start Docker
systemctl enable docker
systemctl start docker
usermod -aG docker ubuntu

# Clone the repo
cd /home/ubuntu
git clone https://github.com/${{GITHUB_REPO:-Enamulitc/mlops-labs-enam}}.git modelserve
cd modelserve/mlops-exam/mlops-exam1/proddetection/modelserve

# Write .env from environment / secrets (injected via GitHub Actions or manually)
cat > .env <<EOF
MLFLOW_S3_BUCKET=s3://{bucket}/mlflow-artifacts
MLFLOW_TRACKING_URI=http://localhost:5000
REDIS_HOST=redis
REDIS_PORT=6379
POSTGRES_USER=mlflow
POSTGRES_PASSWORD=mlflow
POSTGRES_DB=mlflow
EOF

# Pull and start services
docker compose pull
docker compose up -d
""")

# ─────────────────────────────────────────────
# EC2 Instance
# ─────────────────────────────────────────────
ami = aws.ec2.get_ami(
    most_recent=True,
    owners=["099720109477"],   # Canonical (Ubuntu)
    filters=[
        {"name": "name",                    "values": ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]},
        {"name": "virtualization-type",     "values": ["hvm"]},
        {"name": "root-device-type",        "values": ["ebs"]},
    ],
)

instance = aws.ec2.Instance(
    "modelserve-instance",
    ami=ami.id,
    instance_type=instance_type,
    subnet_id=public_subnet.id,
    vpc_security_group_ids=[sg.id],
    iam_instance_profile=instance_profile.name,
    key_name=key_pair_name,
    user_data=user_data,
    root_block_device={"volume_size": 30, "volume_type": "gp3"},
    tags={**project_tag, "Name": "modelserve-instance"},
)

# Elastic IP (make the instance reachable from the internet)
eip = aws.ec2.Eip(
    "modelserve-eip",
    instance=instance.id,
    tags={**project_tag, "Name": "modelserve-eip"},
)

# ─────────────────────────────────────────────
# Stack Outputs
# ─────────────────────────────────────────────
pulumi.export("instance_ip",    eip.public_ip)
pulumi.export("ecr_repo_url",   ecr_repo.repository_url)
pulumi.export("s3_bucket_name", s3_bucket.bucket)
