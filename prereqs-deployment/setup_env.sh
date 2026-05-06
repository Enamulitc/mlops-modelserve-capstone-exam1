#!/usr/bin/env bash
set -euo pipefail

# setup_env.sh
# Create a Python virtual environment, install project dependencies, and
# run small one-off setup tasks (create features.parquet). Intended to be
# run as a non-root developer user after install_prereqs.sh.
#
# Usage:
#   ./prereqs-deployment/setup_env.sh [--minimal]
#
#   --minimal : install a minimal set (pandas, pyarrow, feast[redis]) and
#               finish quickly. By default the script installs the full
#               requirements from requirements.txt so the repo is ready for
#               development and testing.

SCRIPTDIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPTDIR/.." && pwd)
VENV_DIR="$REPO_ROOT/.venv"

# Refuse to run as root to avoid creating root-owned venv files.
if [ "$(id -u)" -eq 0 ]; then
  echo "Do not run setup_env.sh as root. Run it as the normal user who will develop/run the project." 1>&2
  echo "If you previously ran the installer as sudo, re-open your shell (or run 'newgrp docker') and then:" 1>&2
  echo "  ./prereqs-deployment/setup_env.sh" 1>&2
  exit 2
fi

MINIMAL=false
if [ "${1:-}" = "--minimal" ]; then
  MINIMAL=true
fi

echo "Using Python: $(command -v python3) ($(python3 --version 2>/dev/null || echo 'unknown'))"

if [ -d "$VENV_DIR" ]; then
  echo "Reusing existing venv at $VENV_DIR"
else
  echo "Creating venv at $VENV_DIR (python3 -m venv)..."
  python3 -m venv "$VENV_DIR"
fi

# Activate venv
set +u
source "$VENV_DIR/bin/activate"
set -u

python -m pip install --upgrade pip

if [ "$MINIMAL" = true ]; then
  echo "Installing minimal dependencies (pandas, pyarrow, feast[redis])..."
  pip install --no-cache-dir pandas pyarrow feast[redis]
else
  if [ -f "$REPO_ROOT/requirements.txt" ]; then
    echo "Installing full project requirements from requirements.txt (this may take a while)..."
    if pip install --no-cache-dir -r "$REPO_ROOT/requirements.txt"; then
      echo "Full requirements installed successfully."
    else
      echo "Failed to install requirements exactly as pinned. Attempting a relaxed install (will relax scikit-learn pin) and retry..."
      TMP_REQ="/tmp/requirements-relaxed.txt"
      # Relax strict scikit-learn pin if present
      sed 's/^scikit-learn==.*$/scikit-learn>=1.4.0,<1.5/' "$REPO_ROOT/requirements.txt" > "$TMP_REQ" || cp "$REPO_ROOT/requirements.txt" "$TMP_REQ"
      echo "Retrying pip install with relaxed pins (see $TMP_REQ)..."
      if pip install --no-cache-dir -r "$TMP_REQ"; then
        echo "Relaxed requirements installed successfully."
      else
        echo "Relaxed install also failed. Falling back to a minimal best-effort install (pandas, pyarrow, feast[redis], scikit-learn)" 1>&2
        pip install --no-cache-dir pandas pyarrow feast[redis] scikit-learn==1.4.0 || pip install --no-cache-dir pandas pyarrow feast[redis]
        echo "Minimal fallback complete. Some optional packages from requirements.txt may be missing." 1>&2
      fi
    fi
  else
    echo "requirements.txt not found; installing minimal set instead..."
    pip install --no-cache-dir pandas pyarrow feast[redis]
  fi
fi

echo "Running helper to create a minimal training/features.parquet..."
python3 "$REPO_ROOT/scripts/create_dummy_features.py"

# Ensure files are owned by the current user (in case install_prereqs was run with sudo earlier)
chown -R "$(id -u):$(id -g)" "$REPO_ROOT/.venv" || true
chown -R "$(id -u):$(id -g)" "$REPO_ROOT/training/features.parquet" 2>/dev/null || true

echo "Environment setup complete. To activate the venv run:"
echo "  source $VENV_DIR/bin/activate"
echo "You can run tests: pytest -q"

