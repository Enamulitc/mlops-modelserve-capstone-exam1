#!/usr/bin/env bash
set -euo pipefail

# install_prereqs.sh
# Idempotent installer for host-level prerequisites for the project.
# Installs Docker (via get.docker.com), enables the service and adds the
# current user to the docker group. Also installs Python venv support.
#
# Usage:
#   sudo ./prereqs-deployment/install_prereqs.sh
#
LOG(){ printf "[%s] %s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

if [ "$(id -u)" -ne 0 ]; then
  LOG "This script performs system installs and must be run with sudo. Exiting."
  exit 1
fi

apt_get_available(){ command -v apt-get >/dev/null 2>&1; }

if apt_get_available; then
  LOG "Updating apt and installing prerequisite packages..."
  apt-get update -y
  apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg lsb-release python3-venv python3-pip
else
  LOG "apt-get not found on this system. Please install Docker & python venv manually."
  exit 1
fi

# Install Docker using official convenience script if docker not present
if command -v docker >/dev/null 2>&1; then
  LOG "Docker already installed: $(docker --version | tr -d '\n')"
else
  LOG "Downloading Docker install script..."
  curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
  LOG "Running Docker install script..."
  sh /tmp/get-docker.sh
  rm -f /tmp/get-docker.sh
fi

# Enable/start docker if systemctl exists
if command -v systemctl >/dev/null 2>&1; then
  LOG "Enabling and starting Docker service..."
  systemctl enable --now docker
fi

# Add invoking user to docker group (if running under sudo, preserve SUDO_USER)
INVOKER=${SUDO_USER:-$(whoami)}
LOG "Adding user '${INVOKER}' to docker group (may require logout/login)..."
usermod -aG docker "${INVOKER}" || true

LOG "Quick checks:"
LOG "  docker: $(command -v docker >/dev/null 2>&1 && docker --version || echo 'not found')"
LOG "  docker compose: $(docker compose version 2>/dev/null || echo 'not found')"
LOG "  python3: $(command -v python3 >/dev/null 2>&1 && python3 --version || echo 'not found')"

cat <<'EOF'
Done. Next steps (run as your normal user):

  1) Re-open your shell or run:  newgrp docker
     This applies the docker group membership without logging out.

  2) Optionally run the environment setup script to create a Python venv and
     install project dependencies:

       ./prereqs-deployment/setup_env.sh

  3) If you want to start the minimal infra now (postgres, redis, mlflow):

       docker compose up -d postgres redis mlflow

EOF
