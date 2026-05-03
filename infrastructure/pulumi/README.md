# Infrastructure Provisioning

## Architecture Overview

### Terraform
- **Modules**: The infrastructure is divided into modules for better organization and reusability.
  - `vpc`: Creates the VPC and subnets.
  - `s3`: Manages S3 buckets.
  - `ecr`: Manages ECR repositories.
  - `iam`: Manages IAM roles and instance profiles.
  - `security`: Manages security groups.
  - `ec2`: Manages EC2 instances.

### Pulumi
- **Program**: The Pulumi program is written in Python and manages the same resources as Terraform.

## Manual IAM User Creation
1. **Create the IAM User**:
   - Go to the AWS Management Console.
   - Navigate to **IAM** > **Users** > **Add Users**.
   - Enter the username: `mlops-iac-iam-user`.
   - Select **Access key - Programmatic access**.
   - Do **not** enable console access.

2. **Attach the Policy**:
   - Create a custom policy with the following permissions:
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Effect": "Allow",
           "Action": [
             "ec2:*",
             "s3:*",
             "ecr:*",
             "iam:PassRole",
             "iam:GetRole",
             "iam:CreateRole",
             "iam:AttachRolePolicy",
             "iam:DetachRolePolicy",
             "iam:DeleteRole",
             "iam:ListRoles",
             "iam:GetPolicy",
             "iam:CreatePolicy",
             "iam:DeletePolicy",
             "iam:ListPolicies",
             "iam:AttachUserPolicy",
             "iam:DetachUserPolicy",
             "iam:ListAttachedUserPolicies",
             "iam:GetUser",
             "iam:CreateUser",
             "iam:DeleteUser",
             "iam:ListUsers",
             "iam:CreateInstanceProfile",
             "iam:DeleteInstanceProfile",
             "iam:AddRoleToInstanceProfile",
             "iam:RemoveRoleFromInstanceProfile",
             "iam:ListInstanceProfiles",
             "iam:GetInstanceProfile",
             "vpc:*",
             "securityhub:*"
           ],
           "Resource": "*"
         }
       ]
     }
     ```
   - Attach this policy to the `mlops-iac-iam-user`.

3. **Save the Access Key and Secret Key**:
   - After creating the user, download the **Access Key ID** and **Secret Access Key**.

## IAM User Policy

The IAM user policy required for provisioning the infrastructure is provided in the file `iam_user_policy.json`. Follow these steps to attach the policy to the IAM user:

1. Open the AWS Management Console.
2. Navigate to **IAM** > **Users**.
3. Select the user `mlops-iac-iam-user`.
4. Go to the **Permissions** tab.
5. Click **Add permissions** > **Attach policies directly**.
6. Choose **Create policy**.
7. Select the **JSON** tab and copy the contents of `iam_user_policy.json` into the editor.
8. Review and attach the policy to the user.

## Provisioning Steps

### Terraform
1. Navigate to the Terraform directory:
   ```bash
   cd infrastructure/terraform
   ```
2. Initialize Terraform:
   ```bash
   terraform init
   ```
3. Apply the configuration:
   ```bash
   terraform apply
   ```

### Pulumi
1. Navigate to the Pulumi directory:
   ```bash
   cd infrastructure/pulumi
   ```
2. Create a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Deploy the infrastructure:
   ```bash
   pulumi up
   ```