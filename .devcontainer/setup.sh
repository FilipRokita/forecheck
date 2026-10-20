#!/usr/bin/env bash
set -e

# The app's configuration must exist before the container is built: see README.
if [ ! -f .env ]; then
  echo "Missing .env. Create it first: cp .env.example .env, then fill it in." >&2
  exit 1
fi

# Local PostgreSQL 17 + dev role and databases
bash ".devcontainer/db-setup.sh"

# uv runs the Python side; the pinned version is what CI uses
pip install --quiet uv
uv sync --all-groups

# JavaScript dependencies, then the schema
npm ci
npm run db:migrate
