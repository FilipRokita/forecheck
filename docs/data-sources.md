# Data sources

What Forecheck reads, what was verified against the live providers, and what is still an
assumption. The findings below come from `scripts/explore_sources.py` and from the providers'
own documentation, checked on **2026-10-20**. Re-run the script to see whether anything changed.

## Summary

| Question | Answer | Status |
| :--- | :--- | :--- |
| Forecasts of three models for 7 days | Open-Meteo forecast API, one request per station | Verified |
| Chance of rain for each model | Returned for ICON, ECMWF and GFS, but it is the **daily maximum of the hourly chance** | Verified |
| Forecasts as they stood days ago (history) | Previous Runs API, free, **hourly variables only**, from January 2024 | Verified |
| Ground truth | IMGW hourly synoptic archive, rebuilt to UTC days | Verified |
| IMGW live API gives history | No: the latest hourly report only | Verified |
| IMGW daily aggregate files | Not published after June 2024, so days are built from the hourly files | Verified (IMGW notice) |
| IMGW publication lag | A month's file appears about two weeks after the month ends | Verified (3 months observed) |
| IMGW rate limits | None stated in the regulation or on the site | Not documented |
| Dębica has a station | No. Tarnów, about 35 km west, stands in for it | Verified |
| Open-Meteo throttling from shared IPs | Hit during exploration ("Daily API request limit exceeded") | Verified, see below |

## Open-Meteo

Terms: https://open-meteo.com/en/terms. The free API is for **non-commercial use only**: under 10,000
calls a day, 5,000 an hour and 600 a minute, CC BY 4.0, rate limits applied per IP address and application,
and the terms warn that shared hosts such as Vercel, Netlify and Render may be limited earlier.
Forecheck makes about 15 calls a day (one per station).

### Forecast API

- `https://api.open-meteo.com/v1/forecast`, parameters `daily=temperature_2m_mean,precipitation_sum,precipitation_probability_max,wind_speed_10m_mean,pressure_msl_mean`, `models=icon_seamless,ecmwf_ifs025,gfs_seamless`, `forecast_days=8`, `timezone=UTC`, `wind_speed_unit=ms`.
- With several models, every key is suffixed with the model name, for example `temperature_2m_mean_ecmwf_ifs025`.
- Units: °C, mm, m/s (after `wind_speed_unit=ms`), hPa.
- `forecast_days=8` returns the issue day plus 7 days. The issue day is not scored (lead 0).
- `precipitation_probability_max` is returned (non-null) for all three models. **Caveat:** it is the highest
  hourly chance of the day, not the chance of at least 0.1 mm in the day. The Brier score built on it is
  therefore an approximation, and the UI says so.
- The response carries no model run time. NOT VERIFIED whether a run time can be had elsewhere. Forecheck
  uses the fetch time as `issued_at` and counts `lead_days` in UTC days from it. The models start a few hours
  before the fetch, so a "1 day" forecast is slightly fresher than its label. That is the same for all models.

### Previous Runs API (history)

- `https://previous-runs-api.open-meteo.com/v1/forecast`, no key. Most models are archived from January 2024.
- A **daily** variable such as `temperature_2m_mean_previous_day1` is rejected with HTTP 400
  (`Cannot initialize ForecastVariableDaily`). Only **hourly** ones work:
  `temperature_2m_previous_day1` to `_previous_day7`, and the same for `precipitation`, `wind_speed_10m`,
  `pressure_msl`. The adapter rebuilds each UTC day from 24 hours.
- `previous_dayN` is the forecast issued N days before. Forecheck stamps it `issued_at = day - N days, 00:00 UTC`.
- ICON has no `pressure_msl` at a lead of 7 days (all null in the archive). Those scores are simply absent.
- There is no archived chance of rain, so history scores carry no Brier figure.
- A call is weighted by variables times days, so a backfill asks for 31 days at a time.

### Throttling seen in practice

From the exploration environment (a shared IP) the forecast API answered
`{"reason":"Daily API request limit exceeded. Please try again tomorrow."}` after only a handful of calls,
and the connection dropped now and then. This is the risk the terms describe. What Forecheck does about it:

- One request per station per day, spread out, with retries on dropped connections and 5xx answers.
- A "daily" or "hourly" "limit exceeded" answer is not retried: the run stops, reports it, and the next day's run
  continues. A "minutely" one is waited out (60 s) and retried, because it clears with the minute.
- Forecasts missed on a day are not backfilled later: a missing day is a gap, never an invented value.
- `APP_URL` and `CONTACT_EMAIL` go into the User-Agent so that Open-Meteo can tell the instance apart and reach the
  operator. Both are optional and empty by default, so a clone sends nothing that points at someone else.

## IMGW-PIB

Regulation: https://danepubliczne.imgw.pl/regulations. Data may be used free of charge for private purposes
(and for any purpose when the set is classed as high-value data), on condition that the source is named. See
"Required wording" below. The regulation sets **no request limits**. It does say that part of the data may be
unverified (§ 6).

### Live API, not used for scoring

`https://danepubliczne.imgw.pl/api/data/synop` returns the **latest hourly report of 62 stations** and nothing
older. All 15 catalog stations are present. It cannot give a day's mean or total, so it is not the truth source.

### Hourly archive, the truth source

`https://danepubliczne.imgw.pl/data/dane_pomiarowo_obserwacyjne/dane_meteorologiczne/terminowe/synop/`

| Fact | Detail |
| :--- | :--- |
| Layout, current year | One zip per month for all stations, `YYYY_MM_s.zip` |
| Layout, earlier years | One zip per station per year, `YYYY_NNN_s.zip`, NNN = last 3 digits of the station id |
| File | One windows-1250 CSV, 107 columns, **no header row**. The header is `s_t_nagłówek.csv` |
| Times | One report per UTC hour (`GG` 00 to 23) |
| Lag | `2026_07` published 2026-08-31, `2026_08` on 2026-09-30, `2026_09` on 2026-10-16 |
| Status flags | `8` no measurement, `9` no phenomenon. An empty value is not zero |
| Daily files | `dobowe/synop/s_d_t_*` (daily means incl. wind and pressure) stopped in June 2024 (IMGW notice) |

Used columns: `TEMP` (°C), `FWR` (wind speed, m/s, whole numbers), `PPPM` (sea-level pressure, hPa),
`WO6G` (precipitation of the last six hours, mm, reported at 00, 06, 12 and 18 UTC).

How a UTC day is built (`domain/daily.py`):

- Temperature, wind and pressure: the mean of the hourly reports, if at least 20 of 24 are present.
- Precipitation: the sum of the reports at 06, 12 and 18 UTC and the 00 UTC report of the next day, and only
  if all four are present. A missing total could hide rain, so a partial sum is never used.
- A day that fails these rules is not scored.

Checked on September 2026 for all 15 stations: temperature, wind and precipitation were complete for all 29
days checked at every station. **Pressure is missing for Zakopane** (a mountain station with no sea-level
pressure) and complete for 28 of 29 days at Białystok.

### Why the day is a UTC day

Open-Meteo is asked for `timezone=UTC` and IMGW reports hourly in UTC, so both sides cover the same 24 hours.
Using IMGW's own climatological day would not line up: its daily precipitation runs 06 to 06 UTC.

### Required wording

Both lines must appear on every screen that shows data, verbatim. They live in `src/lib/attribution.ts`
and the footer renders them.

> Źródłem pochodzenia danych jest Instytut Meteorologii i Gospodarki Wodnej – Państwowy Instytut Badawczy

> Dane Instytutu Meteorologii i Gospodarki Wodnej – Państwowego Instytutu Badawczego zostały przetworzone

(Regulation § 5. The second line is required because the scores are processed data.) Open-Meteo:
"Weather data by Open-Meteo.com", linked to https://open-meteo.com/, plus the CC BY 4.0 licence.

## Stations

15 stations: ten large cities and five smaller places (Rzeszów, Tarnów, Suwałki, Zakopane, Hel). There is no
synoptic station in Dębica, so Tarnów stands in for it. Coordinates in `application/catalog.py` are the town
or airport of each station to about a kilometre, far finer than the 9 to 28 km model grids.
