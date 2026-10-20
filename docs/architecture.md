# Architecture

## The shape

```
 browser ──► Next.js page (static shell, client-side data)
               │  GET /api/...  (same origin, cached by the CDN)
               ▼
            FastAPI  ─── use cases ─── domain
               │            │
               ▼            ▼
          PostgreSQL     ports ──► adapters ──► Open-Meteo, IMGW
               ▲
               │  once a day, from Vercel Cron
            /api/cron/collect
```

Python owns the data, the database and every calculation. Next.js owns presentation: it formats and shows what the API returns,
and holds no database, no business logic and no secrets.

## Layers (Python)

`backend/forecheck/`. The direction is `entrypoints → infrastructure → application → domain`, and `import-linter` fails the
build if a layer reaches the wrong way (`[tool.importlinter]` in `pyproject.toml`).

| Layer | Holds | May import |
| :--- | :--- | :--- |
| `domain` | Entities, scoring, summable statistics, ranking, trust horizon, daily aggregation rules, the verdict | the standard library |
| `application` | Use cases, read-side queries, the ports (interfaces), the catalog of stations and models, errors | `domain` |
| `infrastructure` | Adapters: Open-Meteo, IMGW, PostgreSQL repositories and unit of work, HTTP client, clock, settings | `application`, `domain`, libraries |
| `entrypoints` | FastAPI app, schemas, routes, the cron route, the composition root | everything below |

`domain` and `application` also may not import FastAPI, Pydantic, SQLAlchemy, psycopg, httpx or pandas: a second contract
checks it.

## Ports

Defined in `application/ports.py`. Every adapter is replaceable without touching a use case.

| Port | Implemented by | Purpose |
| :--- | :--- | :--- |
| `ForecastSource` | `infrastructure/open_meteo.py` | Today's forecasts for the coming week |
| `ForecastArchive` | `infrastructure/open_meteo.py` | Past forecasts at a fixed lead, for history |
| `ObservationSource` | `infrastructure/imgw.py` | Measurements, rebuilt into UTC days |
| `ForecastRepository` | `infrastructure/db/repositories.py` | Forecasts waiting for their day |
| `ObservationRepository` | same | Measured days |
| `ScoreRepository` | same | Summable scores, and the sums over a window |
| `StateRepository` | same | Small facts between runs (which archive versions were read) |
| `RunLogRepository` | same | One row per step of each run |
| `UnitOfWork` | `infrastructure/db/unit_of_work.py` | One transaction across the repositories |
| `Clock` | `infrastructure/clock.py` | The current time, so the use cases are testable |

Each repository has an in-memory twin in `tests/support/memory.py`, and **one contract suite runs against both**
(`tests/contract/`). A use case that passes against the fake can be trusted against PostgreSQL.

## Data model

Created by `migrations/versions/`. `infrastructure/db/tables.py` holds the same definition, and a test compares them, so
they cannot drift.

| Table | Rows | Kept |
| :--- | :--- | :--- |
| `forecasts` | A forecast waiting for its day: station, model, quantity, valid day, lead, `issued_at`, value, chance of rain | Until scored, or 90 days after its day |
| `observations` | One figure per station, quantity and UTC day | Always (tiny) |
| `scores` | `ErrorStats` sums per station, quantity, valid day, model and lead | Always, about 90 MB a year |
| `source_state` | Which version of each IMGW month was read | Always |
| `runs` | One row per step of each daily run | Always (tiny) |

## The daily cycle

`RunDailyCycle` runs three steps in order. A failing step does not stop the others.

1. **Collect.** For each station, one Open-Meteo call (a pause of a second between stations) returns 3 models × 4 quantities × 7
   leads. They are stored with `issued_at` = now. A "limit exceeded" answer stops the step; the rest is left for tomorrow.
2. **Ingest.** Find the oldest waiting forecast. Ask IMGW which months it has published (a directory listing, cheap).
   Read only months whose version changed since the last read. A month is fingerprinted with the next month's version too,
   because the last day of a month needs the first report of the next one.
3. **Evaluate.** For every waiting forecast whose day has a measurement, compute its `ErrorStats`, upsert the score, and
   delete the forecast. Forecasts that stay unmatched 90 days after their day are dropped.

Every step is idempotent. Running the cycle twice changes nothing the second time.

## History (backfill)

`BackfillScores` skips the waiting: it reads measurements for a past range, fetches the Previous Runs archive (forecasts at a
fixed lead), scores them in memory, and writes the scores. It is a script run by hand (`scripts/backfill.py`), never part of
the cron job.

## The API

Read-only, JSON, same origin (`/api/...`). The OpenAPI document is generated from the Pydantic models, and
`src/lib/api/schema.ts` is generated from that with `openapi-typescript`. CI fails if either is stale.

| Endpoint | Returns |
| :--- | :--- |
| `GET /api/meta` | Stations, models, quantities, periods, thresholds, attributions, freshness |
| `GET /api/stations/{id}/verdict` | Best model, trust days, the ranking, how much history there is |
| `GET /api/stations/{id}/horizon` | Every model's figures at every lead |
| `GET /api/comparison` | The best model at every station for one lead |
| `GET /api/stations/{id}/export.csv` | The figures as CSV, with attribution comments |
| `GET /api/health` | Liveness |
| `GET /api/cron/collect` | The daily cycle. Needs `Authorization: Bearer $CRON_SECRET`. Not in the OpenAPI document |

### Caching and abuse

Results change once a day, so every read answers `Cache-Control: public, s-maxage=3600, stale-while-revalidate=86400` and the CDN
absorbs almost all traffic.

A per-IP limiter held in memory does not work on a serverless host (each instance has its own memory and instances come and
go). What works without shared state is **closing the key space**: every parameter is an enum or a small integer, and **unknown
query parameters are rejected with 400**. Otherwise `?x=1`, `?x=2` and so on would skip the cache and reach the database every
time. With it there are only stations × quantities × periods distinct URLs (about 200), all cached. If more is ever needed, a
rate-limit rule belongs in the host's firewall; see [`operations.md`](operations.md).

## Serverless details

- **`NullPool` and `prepare_threshold=None`.** A frozen function instance should not hold idle connections, and Neon's pooler
  (PgBouncer in transaction mode) cannot honour the server-side prepared statements psycopg starts after five uses.
- **`api/index.py` is a shim.** Vercel turns every Python file in `api/` into a function, so the package lives in `backend/` and
  the shim puts it on the path. Only runtime dependencies are installed there (20 packages, about 50 MB); everything else is in
  dependency groups.
- **Migrations run in the production build** (`vercel.json`), through `scripts/migrate.sh`. It uses `uv` when present and a
  throwaway virtual environment with pinned requirements when not, so it works in a plain Node build image. If it fails, the
  build stops and nothing is deployed.

## Decisions

| Decision | Why | Not chosen |
| :--- | :--- | :--- |
| Scheduled job on **Vercel Cron**, once a day | One platform, no secrets in GitHub, no workflow that switches itself off after 60 days of repository inactivity, and it fits the "set the variables and it runs" goal. 15 calls a day is far below any limit | GitHub Actions `schedule`: better isolated from Open-Meteo's shared-IP throttling, but needs repository secrets, is delayed under load, and its terms limit Actions to work on the repository's own software |
| **Hourly** IMGW archive for truth | The live API has no history, and the daily files IMGW published stopped in June 2024. The hourly files let a UTC day be rebuilt exactly and line up with Open-Meteo's days | IMGW's daily aggregates (a different day boundary, precipitation 06 to 06 UTC) |
| **Summable scores** instead of keeping raw pairs | Storage stays flat, every period is one SQL sum, and the algebra is testable as a property | Keeping every forecast and measurement pair: more storage, and nothing the page shows needs it |
| **Python in `backend/`**, a thin `api/index.py` | Vercel makes every file in `api/` a function. The package stays importable and testable, and only one function exists | The whole package inside `api/` |
| **No Vercel Services** | The docs describe it as beta. The classic layout (Next.js plus a Python function) is the stable path | Services |
| **Client-side data fetching** | The page needs no server work: a static shell and cached JSON. The same relative URLs work in development and in production | Server components calling the API, which would need an absolute URL and a second cache |
| **pandas only in scripts** | The API and the domain need none of it, and keeping it out keeps the function at 50 MB | pandas in the request path |
| **No accounts** | Nothing here is personal. The remembered station lives in the browser. The ports leave room for accounts later; see [`extending.md`](extending.md) | A login |
