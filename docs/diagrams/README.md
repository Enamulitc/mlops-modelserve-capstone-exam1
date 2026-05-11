# Architecture Diagrams

This directory contains image versions of the architecture diagrams documented in
[`../ARCHITECTURE.md`](../ARCHITECTURE.md).

## Diagrams

| File | Description |
|------|-------------|
| `local-topology.png` | Local development topology (Docker Compose on developer machine / Poridhi VM) |
| `production-topology.png` | Production topology — Single EC2 node on AWS with GitHub Actions CI/CD, ECR, and S3 |

> **Note:** The ASCII diagrams in `ARCHITECTURE.md` (Section 2) are the authoritative
> source. The images here are rendered for readability during the live demo and TA review.
> If you regenerate these images (e.g., from Excalidraw or draw.io), commit them here and
> update the filenames in this README.
