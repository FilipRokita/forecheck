#!/usr/bin/env bash
set -e

# On every start: bring the database back up,
bash ".devcontainer/db-start.sh"
# and apply any new migrations.
npm run db:migrate
# Start the app with: npm run dev
