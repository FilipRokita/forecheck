# Operations

Deploying Forecheck, what runs and when, and what to do when something does not.

## What you need

| Account | Plan | Why | Card needed |
| :--- | :--- | :--- | :--- |
| [Vercel](https://vercel.com) | Hobby | Hosts the page and the Python API, and runs the daily job | No |
| [Neon](https://neon.com) | Free | PostgreSQL | No |

Both are free for this use. The Vercel Hobby plan is for **non-commercial** use only, as is the Open-Meteo free tier, which
fits: no ads, no subscriptions, no paid features. Adding any of those means moving to paid plans on both sides, and getting a
commercial licence for the Open-Meteo data.

## Deploy

1. **Neon.** Create a project. From its connection details copy two strings: the **pooled** one (the host has `-pooler` in it)
   and the **direct** one.
2. **Vercel.** Import the repository. It detects Next.js. Leave the build settings alone: `vercel.json` sets them.
3. **Environment variables** (Project Settings, Environment Variables, for Production):

| Variable | Value | Notes |
| :--- | :--- | :--- |
| `DATABASE_URL` | Neon pooled connection string | Used by the API. `postgres://` and `postgresql://` are accepted as pasted |
| `DIRECT_URL` | Neon direct connection string | Used by migrations only. A pooler in transaction mode does not suit DDL |
| `CRON_SECRET` | a random string of 16+ characters | `openssl rand -base64 32`. Vercel sends it with every cron call. Without it the cron route is off |
| `APP_URL` | the address of your deployment | Goes into the User-Agent of every request to Open-Meteo and IMGW, so they can tell your instance apart. Optional |
| `CONTACT_EMAIL` | your address | Goes into the same User-Agent, so the providers can reach you. Recommended |

Optional: the method's thresholds ([`spec.md`](spec.md#settings)). Leave `NEXT_PUBLIC_API_BASE_URL` empty (the page and the API
share an origin) and ignore `API_PROXY_TARGET` (development only).

4. **Deploy.** The production build runs `npm run db:migrate` before `next build`. If the migration fails, the build fails and
   nothing is deployed. The tables are created on the first deploy.

Preview deployments do not migrate, and they use whatever `DATABASE_URL` is set for Preview. If a branch changes the schema,
give Preview its own Neon branch and database, or its pages will fail against the old schema.

## The daily job

`vercel.json` schedules `GET /api/cron/collect` at 09:23 UTC, once a day.

- **Timing.** On the Hobby plan a job runs at most once a day, and Vercel starts it somewhere in the hour that follows the
  time given (a job set for 09:23 may start between 09:00 and 09:59; the precision on Hobby is "per hour"). 09:23 UTC is
  late enough for the 00 UTC runs of all three models to be out.
- **Security.** Vercel sends `Authorization: Bearer <CRON_SECRET>`. The route compares it in constant time and answers 401 when
  it differs, and 404 when no secret is set.
- **Duration.** About 15 forecast calls with a second between them, one directory listing, a zip of 1 to 2 MB when IMGW has
  republished a month, and some SQL: well under a minute. The function limit is set to 300 s.
- **Failure.** Vercel does not retry a failed cron call. The route answers **502 when any step failed**, so the failure shows
  in Vercel's cron log, and the next day's run carries on. A missed day is a gap, never an invented value.
- **Safe to run by hand.** Every step is idempotent. To run it now:
  `curl -H "Authorization: Bearer $CRON_SECRET" https://your-app.vercel.app/api/cron/collect`

What a run does is described in [`architecture.md`](architecture.md#the-daily-cycle).

### Starting with a history

A fresh install has nothing scored, and the first scores arrive about two weeks after a month ends. To start with months of
history instead, run the backfill once from your own machine:

```bash
# .env must point DATABASE_URL at the database to fill (the Neon direct string works well)
uv run python scripts/backfill.py --days 60
```

It reads IMGW's published months, replays Open-Meteo's archived forecasts for the same days, and writes the scores. A day that already has a score from a live forecast keeps it. It makes one
Open-Meteo call per station and 31 days (15 calls for 60 days), pauses between stations, and is safe to repeat. If the
provider's daily limit is hit it stops, keeps what it scored, and can simply be run again later (`--stations` limits it). It
never runs from the scheduled job.

The archive covers January 2024 onwards for most models, and has no chance of rain, so history has no Brier score.

## Freshness and health

- `GET /api/meta` includes `status`: the latest scored day, how many forecasts are waiting, and the last result of each step
  (`collect`, `ingest`, `evaluate`) with its time and message.
- "Scored through" on the page is that latest scored day. A gap of up to about six weeks between it and today is normal:
  IMGW publishes a month about two weeks after it ends.
- Vercel's Cron Jobs view and function logs show each run.

## Limits and what is used

| Resource | Limit | Use |
| :--- | :--- | :--- |
| Open-Meteo calls | under 10,000 a day, 5,000 an hour, 600 a minute (checked in its terms) | about 15 a day, plus 15 per 60 days of backfill |
| Neon Free storage | 1 GB per project (checked on Neon's pricing page, 2026-10-20) | about 90 MB a year: 1,260 score rows a day at 195 bytes each, measured |
| Neon Free compute | 100 CU-hours a month, scales to zero after 5 minutes idle | a minute or two a day for the job, plus cache misses |
| Vercel Hobby cron | once a day, hour precision | one job |
| Vercel function | 300 s, 500 MB bundle | under a minute, about 50 MB |

If Neon's compute allowance or Open-Meteo's quota runs out, the provider suspends or refuses, and the app degrades the way it
should: the page serves what is stored (and cached), and the daily job reports the failure.

### Abuse

Reads are cheap aggregates behind a CDN cache, and the API rejects unknown query parameters, so the set of URLs that can reach
the database is small and fixed ([`architecture.md`](architecture.md#caching-and-abuse)). If traffic ever warrants more, add a
rate-limit rule in Vercel's firewall for `/api/*`. A limiter inside the app would not work: serverless instances share no memory.

## Troubleshooting

| Symptom | Likely cause and what to do |
| :--- | :--- |
| Build fails at `db:migrate` | `DIRECT_URL` is wrong or the Neon project is suspended. Fix it and redeploy. If the build environment cannot run Python at all, run `npm run db:migrate` from your machine with `DIRECT_URL` set, then remove the migrate step from `buildCommand` in `vercel.json` |
| Page says "Could not load the app" | The API function failed. Look at its logs. Usually `DATABASE_URL` is missing or malformed |
| Page says "Nothing is scored yet" | Normal on a new install. Run the backfill, or wait for the first month to be published |
| Cron answers 401 | `CRON_SECRET` differs between the variable and what is sent. Re-save it and redeploy |
| Cron answers 502 | A step failed. The response body names it. `collect` with "rate limiting" means Open-Meteo refused for the day, and tomorrow's run continues |
| "Daily API request limit exceeded" | Open-Meteo throttles by IP address, and shared hosts hit the limit sooner than their own traffic would. The run stops and retries tomorrow. If it persists, run the job from another network, or contact Open-Meteo |
| Scores stop advancing | IMGW has not published the next month yet (normal, up to about two weeks), or its directory layout changed. Run `uv run python scripts/explore_sources.py` and compare with [`data-sources.md`](data-sources.md) |

## Verification status

What has been checked, and where, so that nobody reads a claim as stronger than it is.

| Claim | Status |
| :--- | :--- |
| Domain, adapters (on recorded provider responses), use cases, API, view | Tested in CI-style runs: the Python tests (including against PostgreSQL 16) and the view tests |
| Open-Meteo forecast and Previous Runs response formats | **Verified live** on 2026-10-20 and recorded as fixtures |
| IMGW archive layout, lag, file format, completeness at 15 stations | **Verified live** on 2026-10-20 |
| IMGW data for the whole of last month rebuilds into complete days | **Verified live** (29 of 29 days for temperature, wind, precipitation at all 15 stations) |
| Migrations run with only `python3` and `pip` (no `uv`), and are idempotent | **Verified** locally in a clean environment |
| The function imports with only runtime dependencies (20 packages, about 50 MB) | **Verified** locally |
| The Vercel build can run Python, create a virtual environment and install packages | **Not verified.** Needs a first deploy. Fallback in the table above |
| Vercel imports `backend/` from `api/index.py` and keeps the original path for the rewritten `/api/*` calls | **Not verified.** Needs a first deploy. The shim is the documented-safe layout, and a fallback is a one-line change to `vercel.json` |
| Vercel invokes cron with GET, only on production, with the secret as a bearer token | Per Vercel's documentation, not exercised here. The secret header was confirmed in the docs |
| Backfill against live Open-Meteo | **Not run end to end.** Its quota was exhausted from the build environment (see data-sources). The adapter is tested on a real recorded response, the use case on fakes and the database |
| Neon pooled connections with `prepare_threshold=None` | By design (psycopg and PgBouncer documentation), **not exercised** against Neon |
| GitHub Actions workflow | Syntax and commands run locally, **not run on GitHub** |
