#!/usr/bin/env bash
# Applies the database migrations (Alembic) on the DIRECT_URL, falling back to
# DATABASE_URL. Used by `npm run db:migrate`, the dev container and the host
# build. It needs only python3 with pip, so it also runs in a Node build image.
#
# If this step fails on the host, the build stops before anything is deployed.
set -euo pipefail
cd "$(dirname "$0")/.."

# Locally the settings live in .env; on a host they are already in the environment. Variables that
# are already set win over .env, so an explicit DIRECT_URL always beats the file.
if [ -f .env ]; then
  while IFS='=' read -r key value; do
    case "$key" in '' | '#'*) continue ;; esac
    if [ -z "${!key+x}" ]; then export "$key=$value"; fi
  done < .env
fi

if command -v uv >/dev/null 2>&1; then
  exec uv run --group migrate alembic upgrade head
fi

VENV=".migrate-venv"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --disable-pip-version-check -r requirements/migrate.txt
exec "$VENV/bin/alembic" upgrade head
