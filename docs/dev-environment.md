# Dev environment

How the development environment is set up and configured.

Everything runs inside a dev container. Open the repo in VS Code and choose
**Dev Containers: Reopen in Container** (or **Rebuild Container**).

## Before you start

Create the environment file from its committed template:

```bash
cp .env.example .env
cp .mcp.example.json .mcp.json   # optional, for the Context7 MCP server
```

The container build stops with a clear message if `.env` is missing. The defaults work locally.

## Configuration and secrets

`.env` holds the database URL, the cron secret and a contact address. It is gitignored, with a committed `.env.example`
counterpart. The Python side reads it through `pydantic-settings`, and `scripts/migrate.sh` reads it too (variables already in
the environment win over the file).

## The dev container

The container definition lives in `.devcontainer/`:

- `devcontainer.json` configures the image (Node.js 24 on Debian Trixie), features (GitHub CLI, Python 3.13), VS Code extensions,
  ports 3000 and 8000, and `TZ=UTC`, so dates behave the same as on a host.
- `setup.sh` runs once as `postCreateCommand`. It needs `.env` to exist, then installs PostgreSQL, `uv` and the Python
  dependencies (`uv sync --all-groups`), the JavaScript dependencies (`npm ci`), and applies the migrations.
- `db-setup.sh` installs PostgreSQL 17 and creates the `forecheck` role with two databases: `forecheck` for development and
  `forecheck_test` for the tests. It is safe to run again.
- `db-start.sh` starts the PostgreSQL cluster if it is not running.
- `start.sh` runs on every start (`postStartCommand`): it brings the database back up and applies any new migrations.

## Running the app

```bash
npm run dev          # Next.js on :3000 and the API (uvicorn) on :8000, side by side
```

Open **http://localhost:3000**. Use `localhost`, not `127.0.0.1`: the Next.js dev server blocks other hostnames for its
development resources, and the page would not become interactive. Next.js proxies `/api/*` to the API in development
(`next.config.ts`), so the page and the API share one origin, as they do in production.

## Data to look at

The database starts empty, and the page says so. Two ways to fill it:

| Command | What it does |
| :--- | :--- |
| `uv run python scripts/seed_demo.py` | Made-up scores for 15 stations, flagged "Sample data" on the page. `--clear` removes them |
| `uv run python scripts/backfill.py --days 60` | Real history from the Open-Meteo archive and IMGW. See [operations](operations.md#starting-with-a-history) |

## Checks

| Command | What it checks |
| :--- | :--- |
| `uv run ruff check . && uv run ruff format --check .` | Lint and formatting (Python) |
| `uv run mypy` | Types, `--strict` |
| `PYTHONPATH=backend uv run lint-imports` | The layer contracts |
| `uv run pytest` | All Python tests. The ones that need PostgreSQL run against `TEST_DATABASE_URL` and are skipped without it |
| `npm run lint` | ESLint, including the import rules between layers |
| `npm run typecheck` | `next typegen` and `tsc --noEmit` |
| `npm test` | Vitest: unit, component and integration tests of the view |
| `npm run api:types:check` | The OpenAPI document and the generated types are current |
| `npm run build` | The production build |
| `npm run check:py` | The Python checks above, in one go |

To run the PostgreSQL tests locally:

```bash
TEST_DATABASE_URL=postgresql://forecheck:forecheck@localhost:5432/forecheck_test uv run pytest
```

They drop and recreate the schema of that database, so never point it at a database you care about.

CI runs the same commands on every push to `main` and on every pull request (`.github/workflows/ci.yml`).

## Changing the API

The Pydantic models in `backend/forecheck/entrypoints/http/schemas.py` are the contract. After changing one:

```bash
npm run api:types       # rewrites openapi.json and src/lib/api/schema.ts
```

Commit both generated files. CI fails if they are stale.

## Changing the schema

Write a new migration by hand in `migrations/versions/`, and update `backend/forecheck/infrastructure/db/tables.py` to match.
A test compares the migrated schema with the table definitions, so a mismatch fails.

## A slow checkout

If the repository sits on a mounted Windows drive, installs and builds take minutes and hot reload does not work. Clone it
inside the container's own disk for a fast loop.
