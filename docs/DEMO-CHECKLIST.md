# Demo Checklist for TA

This checklist is designed to guide the live demo. Each step should take < 2 minutes.

1. Repo overview
   - Show `README.md` and `docs/ADRs/0001-terraform-vs-pulumi.md` (explain choice)
2. Start local stack
   - `docker compose up -d --build`
   - Show MLflow UI: http://localhost:5000
3. Run training (optional)
   - `.venv/bin/kaggle datasets download -d kartik2112/fraud-detection -p training/ --unzip`
   - `.venv/bin/python training/train.py`
   - Show model registered in MLflow model registry
4. Materialize features
   - Run the ephemeral container command in `docs/DEPLOYMENT.md`
   - Show Redis keys (optional)
5. Test API
   - `curl -X POST http://localhost:8000/predict -d @training/sample_request.json`
   - Show Grafana dashboard panel with prediction requests/latency
6. Show CI run
   - Open GitHub Actions run that built & pushed image
7. Deploy to EC2
   - Show that the EC2 instance pulled the image and `docker compose up -d` restarted api with new image
8. Teardown
   - `terraform destroy` (or `pulumi destroy` if added)

Good to know: Keep `.env` secret values out of the repo. Use Repository Secrets for GitHub Actions. The EC2 instance uses an instance profile for S3/ECR pull operations.
