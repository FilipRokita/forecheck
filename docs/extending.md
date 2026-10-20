# Extending

How to change what Forecheck watches, and how to grow it. Each section names the files to touch. If a change needs more than
that, the architecture is wrong, and that is worth knowing.

## Add a station

Append a `Station` to `DEFAULT_CATALOG` in `backend/forecheck/application/catalog.py`:

```python
(Station(StationId("12295"), "Białystok", 53.107, 23.162),)
```

- The id is the IMGW station id. The list is at https://danepubliczne.imgw.pl/api/data/synop. The last three digits must be
  distinct among the catalog's stations (a test checks it), because they pick the right rows out of IMGW's archive files.
- Coordinates are the station's town or airport, to about a kilometre.
- Nothing else changes: the stations in the page, the API and the CSV all come from the catalog. History for a new station
  comes from `scripts/backfill.py --stations <id>`.

## Add a model

Append a `ModelSpec` to the catalog: an id, a label, and the name Open-Meteo knows the model by.

```python
(ModelSpec(ModelId("meteofrance"), "ARPEGE", "meteofrance_seamless"),)
```

Pick the name from Open-Meteo's model list. Then give the model a colour in `src/lib/models.ts` and a `--color-model-*` token
in `src/app/globals.css`. Without a colour it still shows, in grey, with its name.

## Add a quantity

1. `Variable` in `domain/types.py`: a value and a unit. Say whether it is an event (yes/no) like rain.
2. A trust bar in `Rules` (`domain/rules.py`) and a setting for it in `infrastructure/settings.py`.
3. The Open-Meteo parameter names in `infrastructure/open_meteo.py` (`_DAILY` and `_HOURLY`).
4. How IMGW measures it, in `infrastructure/imgw.py` and, if it needs a new aggregation rule, `domain/daily.py`.
5. A label in `entrypoints/http/presenters.py`.

Run `npm run api:types`. The page lists quantities from the API, so it needs no change.

## Change the forecast provider

Write a class with the methods of `ForecastSource` (and `ForecastArchive` if it has an archive) in `infrastructure/`, and use it
in `entrypoints/composition.py`. Nothing in `domain` or `application` changes. Keep the rules that make the scores honest:
issue time stored with the forecast, days in UTC, units in °C, mm, m/s and hPa.

Test it the way the others are: record a real response into `tests/fixtures/`, and serve it with `respx`.

## Change the measurements provider

The same, for `ObservationSource`: return one `Observation` per station, quantity and UTC day, leave out days you cannot
build properly, and report which months are available with a version that changes when they are republished.

## Move the database

Everything goes through the repository ports. Another SQL database means a new `infrastructure/db/` and a new migration
history. The tests in `tests/contract/` are the specification: run them against the new implementation.

## Add accounts and users

Nothing here is personal today, so there is no user model. To add one without touching the scoring:

1. **A port.** `UserRepository` and `Sessions` (or `IdentityProvider`) in `application/ports.py`, with an in-memory twin and a
   contract test, as the other repositories have.
2. **An adapter.** Either your own tables (a migration, a repository) or an external provider behind the same port.
3. **A dependency.** `current_user` in `entrypoints/http/deps.py`, used only by the routes that need it. The read endpoints stay
   public and cacheable: a response that depends on the user must not carry `s-maxage`.
4. **Settings.** Replace the browser-only remembered station (`src/lib/selection.ts`) with a saved preference behind the port.
5. **The view.** A sign-in page and a small client for the new endpoints, generated from the same OpenAPI document.

Per-user data would end the "no personal data" simplicity, so decide first what is stored and for how long.

## Leave Vercel

The code does not depend on Vercel. The API is a standard ASGI app (`backend/forecheck/entrypoints/http/app.py`), the page is a
standard Next.js app, the job is one HTTP route, and the only coupling is `vercel.json` (the build step, the rewrite, the
cron). Elsewhere: run `uvicorn` for the API and `next start` for the page behind one origin, call
`/api/cron/collect` from any scheduler with the bearer token, and run `npm run db:migrate` on deploy. A Dockerfile is not
included because nothing needs it yet.
