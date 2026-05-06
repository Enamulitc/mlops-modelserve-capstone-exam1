# Infrastructure — IAM Policies Reference

## EC2 Instance Role

| Field       | Value                              |
|-------------|------------------------------------|
| Role Name   | `modelserve-ec2-workload-role`     |
| Policy Name | `modelserve-ec2-s3-ecr-access`     |
| File        | `ec2_role_policy.json`             |

**Purpose:** Attached to the EC2 instance (role-based, no static credentials needed).
- **S3** — Read/write access to `modelserve-artifacts-8e460886` (MLflow artifact store)
- **ECR** — Pull-only access (login + pull images deployed by GitHub Actions)

> ECR **push** is performed by the GitHub Actions IAM user, not this role.

---

## GitHub Actions IAM User

| Field       | Value                              |
|-------------|------------------------------------|
| Policy Name | `mlops-iac-user-policy`            |
| File        | `mlops_iac_iam_user_policy.json`   |

**Purpose:** Used by GitHub Actions CI/CD secrets (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`).
- EC2, VPC, S3, ECR (full including push), IAM — for Terraform/Pulumi IaC and image builds

---

## S3 Bucket

| Field  | Value                                   |
|--------|-----------------------------------------|
| Bucket | `modelserve-artifacts-8e460886`         |
| Region | `ap-southeast-1`                        |
| Use    | MLflow artifact store (model.pkl, etc.) |
