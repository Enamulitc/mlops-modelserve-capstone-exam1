# ADR 0001 — Terraform vs Pulumi

Status: Accepted
Date: 2026-05-07

## Context

The exam guidance requests Pulumi for infrastructure provisioning. During the lab work, the provided internal VM could not be updated (network/apt issues) and Python/Pulumi could not be installed reliably. To complete the assignment on time and produce a working end-to-end system, infrastructure was provisioned in the author's personal AWS account using Terraform (familiar and testable).

## Decision

Use Terraform in this repository for provisioning the required AWS resources. Document the decision and provide a migration plan and mapping to Pulumi.

## Consequences

- Pros: Fast delivery, tested Terraform code, reproducible deployment in the author's AWS account. Easier to manage given the lab constraints.
- Cons: Deviates from the exam's requested IaC tool (Pulumi). To mitigate this, we provide an ADR, mapping notes, and a migration plan so graders can validate equivalence.

## Migration plan (short)

1. Create a Pulumi project (Python) that defines the same resources: S3, ECR, EC2, IAM roles, security groups.
2. Where possible import existing resources into Pulumi state using `pulumi import`.
3. Add a CI job that runs `pulumi preview` for reviewers.

## Notes

This ADR documents a pragmatic decision driven by environment constraints. The rest of the repo is designed to be compatible with Pulumi later (artifact locations use env vars, IAM and resource names are configurable).
