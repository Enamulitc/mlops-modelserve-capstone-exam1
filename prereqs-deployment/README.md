Prereqs deployment helper scripts
=================================

This folder contains convenience scripts to prepare a host for running the
ModelServe project. They are intended to be idempotent and easy to run after
infrastructure provisioning.

Files
-----

- `install_prereqs.sh`  — Run with `sudo` to install Docker, system packages,
  and add the invoking user to the `docker` group.
- `setup_env.sh`        — Run as a normal user to create a Python virtualenv and
  install either minimal or full Python dependencies. Also runs helper to
  create `training/features.parquet` so Feast materialization works.

Usage (recommended)
-------------------

1. SSH into the provisioned server.
2. Run the system installer (requires sudo):

     sudo ./prereqs-deployment/install_prereqs.sh

3. Either open a new shell (to pick up docker group) or run `newgrp docker`.
4. Set up the Python environment (non-root):

     ./prereqs-deployment/setup_env.sh --full   # to install full requirements
     or
     ./prereqs-deployment/setup_env.sh         # minimal install (fast)

5. Start the minimal infra and continue with the project steps in the repo
   README.

Notes
-----
- The scripts aim to be portable for Ubuntu-based images. If your environment
  uses a different package manager, adapt the `install_prereqs.sh` accordingly.
- `setup_env.sh --full` installs all packages from `requirements.txt` and will
  take longer. The minimal mode installs packages necessary for the setup
  helper and Feast CLI so you can apply/materialize features.
