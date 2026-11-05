# 🗂️ Repo layout

What every entry in the repository root is for.

## Committed and tracked

| Path | What it is |
| :--- | :--- |
| [`README.md`](../README.md) | Project overview: what Forecheck does, the stack, how to run it locally and on a host. |
| [`AGENTS.md`](../AGENTS.md) | Instructions and rules for AI agents working in this repository. |
| [`LICENSE`](../LICENSE) | MIT, for the code. The data keeps its own terms. |
| [`docs/`](.) | Everything that is not in the README: the guides, the README's screenshots (`images/`) and its logo (`brand/`, the app icon with the wordmark, in a light and a dark version). |
| [`.devcontainer/`](../.devcontainer/) | Dev container configuration and setup scripts. See [Dev environment](dev-environment.md). |
| [`.github/workflows/`](../.github/workflows/) | CI only. The scheduled job runs on Vercel Cron, not here. |
| [`.env.example`](../.env.example) | Template for the application's `.env`. Copy it before the first run. |
| [`.mcp.example.json`](../.mcp.example.json) | Template for the local `.mcp.json`: MCP servers in the format Claude Code reads (Context7). |
| [`.gitignore`](../.gitignore), [`.gitattributes`](../.gitattributes), [`.python-version`](../.python-version) | Untracked files, line endings, the Python version. |
| [`package.json`](../package.json) / `package-lock.json` | JavaScript dependencies, pinned versions and the npm scripts. |
| [`pyproject.toml`](../pyproject.toml) / `uv.lock` | Python dependencies in groups, and the configuration of ruff, mypy, pytest and import-linter. |
| [`requirements/migrate.txt`](../requirements/migrate.txt) | Pinned requirements for the migration step on a host. Generated from the lockfile, and CI checks it is current. |
| [`src/`](../src/) | The view (Next.js). See [Project structure](#project-structure). |
| [`backend/forecheck/`](../backend/forecheck/) | The Python package: domain, application, infrastructure, entrypoints. |
| [`api/index.py`](../api/index.py) | The Vercel function: a shim that imports the app from `backend/`. |
| [`migrations/`](../migrations/) / [`alembic.ini`](../alembic.ini) | Alembic migrations, written by hand. |
| [`tests/`](../tests/) | pytest: `unit/` (domain with hypothesis, adapters on recorded responses, use cases, API), `contract/` (repositories, run against memory and PostgreSQL), `integration/` (PostgreSQL), `fixtures/` (real recorded provider responses). |
| [`scripts/`](../scripts/) | `migrate.sh`, `explore_sources.py`, `backfill.py`, `seed_demo.py`, `export_openapi.py`. |
| [`openapi.json`](../openapi.json) | The API's OpenAPI document, generated. CI checks it is current. |
| [`vercel.json`](../vercel.json) | The host's build command (migrate on production builds), the API rewrite, the daily cron, the function limits and which branches deploy (only `main`). |
| [`next.config.ts`](../next.config.ts), [`tsconfig.json`](../tsconfig.json), [`eslint.config.mjs`](../eslint.config.mjs), [`postcss.config.mjs`](../postcss.config.mjs), [`vitest.config.ts`](../vitest.config.ts) | Tool configuration. |

## Files you create yourself

These are gitignored, so you create each one from its committed template.

| Path | Created from | What it holds |
| :--- | :--- | :--- |
| `.env` | [`.env.example`](../.env.example) | The database URL, the cron secret, the contact address and the app URL. |
| `.mcp.json` | [`.mcp.example.json`](../.mcp.example.json) | MCP server configuration, with an optional Context7 key. |

## Project structure

```
backend/forecheck/
  domain/          pure Python: scoring, statistics, ranking, trust horizon, verdict
  application/     use cases, read-side queries, ports, the catalog of stations and models
  infrastructure/  Open-Meteo and IMGW adapters, PostgreSQL, HTTP client, settings
  entrypoints/     FastAPI app, schemas, routes, cron route, composition root
src/
  app/             the page, layout, tokens (globals.css)
  components/      the dashboard and its parts
  lib/             formatting, chart scale, selection, attribution
  lib/api/         the API client, its hook, and the generated types
```

The import rules between layers are enforced by `import-linter` on the Python side (`pyproject.toml`) and by ESLint on the
view side (`eslint.config.mjs`). On the Python side the rule that matters is: **`domain` imports only the standard library**.
On the view side: `app → components → lib → lib/api`, never the other way.
