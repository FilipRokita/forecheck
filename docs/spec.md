# Specification

What Forecheck measures, exactly, and where the method is weak. The code that implements it is in
`backend/forecheck/domain/`. Every rule here is a function or a setting there, with tests.

## The question

At a given station, for a given quantity, which model's forecasts have been closest to what was measured, and how many days
ahead does that model stay good enough to rely on?

## Definitions

| Term | Meaning |
| :--- | :--- |
| Station | One of 15 IMGW synoptic stations in `application/catalog.py` |
| Model | DWD ICON (`icon_seamless`), ECMWF IFS (`ecmwf_ifs025`), NOAA GFS (`gfs_seamless`), as served by Open-Meteo |
| Quantity | Temperature (daily mean, °C), precipitation (daily sum, mm), wind (daily mean speed, m/s), pressure (daily mean, sea level, hPa) |
| Day | A **UTC** day, for forecasts and measurements alike |
| Issued | The UTC time a forecast was fetched. `issued_at` |
| Lead | Whole UTC days from the issue day to the day forecast, 1 to 7. `lead_days` |
| Truth | What the station measured, rebuilt into a UTC day. Nothing else counts |

**A forecast is never refreshed.** It is stored with the time it was fetched, and it is scored against the day it was about,
as it stood then. Lead 0 (the issue day itself) is not scored, because part of that day has already happened.

## Truth

Station measurements only. IMGW's hourly synoptic reports are rebuilt into UTC days:

- Temperature, wind, pressure: the mean of the hourly reports, if at least 20 of 24 exist.
- Precipitation: the sum of the six-hour totals reported at 06, 12 and 18 UTC and at 00 UTC of the next day, only if all
  four exist. A missing total could hide rain, so a partial sum is never used.
- A day that fails these rules is not scored at all.

Reanalysis (ERA5 and the like) is a model, not a measurement, and is never used as truth. How the archive is read, and what
was verified about it, is in [`data-sources.md`](data-sources.md).

## Scoring one forecast

For a forecast `f` and a measurement `o` of the same station, quantity and day, with `e = f - o`:

| Figure | Kept as a sum |
| :--- | :--- |
| Samples | `n` |
| Absolute error | `sum |e|` |
| Signed error (bias) | `sum e` (positive means the model runs high) |
| Squared error | `sum e²` |

For precipitation a day is **wet** when at least `precipitation_threshold_mm` (default 0.1) fell. The forecast and the
measurement are each wet or dry, which gives four counts: hits, misses, false alarms, correct negatives. When the provider
gave a chance of rain `p`, the **Brier** term `(p - wet)²` is added as well.

## Summable statistics

One `ErrorStats` is stored per station, quantity, model, lead and valid day. It is a bundle of sums, and adding two of them
gives the statistics of the two sets together (this is a monoid, and the tests check it as a property). So:

- a ranking over 30 days, 90 days or 12 months is one SQL `SUM` over the matching rows;
- the raw forecast is deleted once scored, and storage grows by about 90 MB a year (measured: 195 bytes a row, 1,260
  rows a day) until scores reach two years of age, when they are dropped, so it levels off near 180 MB;
- derived figures are computed on read:

| Figure | Formula |
| :--- | :--- |
| Mean absolute error (MAE) | `sum |e| / n` |
| Bias | `sum e / n` |
| RMSE | `sqrt(sum e² / n)` |
| Accuracy | `(hits + correct negatives) / days` |
| Hit rate | `hits / (hits + misses)` |
| False alarm ratio | `false alarms / (hits + false alarms)` |
| Brier score | `sum (p - wet)² / days with a p` |

A figure with an empty denominator is absent, never zero.

## Ranking

Over leads 1 to `ranking_lead_max` (default 3), added together, per station and quantity:

- measured quantities: lowest MAE first, then lowest RMSE;
- precipitation: highest accuracy first, then lowest Brier, then lowest MAE;
- ties fall to the model name, so the order is stable.

A model with fewer than `min_samples` (default 10) scored days is listed but not ranked, and it can never be the "most
accurate model". Days are counted at the lead where the model has the fewest, not as the forecasts summed over the leads (which would count
each day up to `ranking_lead_max` times). A model that lacks one of those leads is unranked, because error grows with lead and
models summed over different leads cannot be compared.

## Trust horizon

The **largest lead N such that every lead from 1 to N meets the bar**. It stops at the first lead that fails or that has
fewer than `min_samples` days, so a lucky day 5 behind a bad day 3 does not extend it.

| Quantity | The bar for a lead |
| :--- | :--- |
| Temperature | MAE at most 2.0 °C |
| Wind | MAE at most 1.5 m/s |
| Pressure | MAE at most 2.0 hPa |
| Precipitation | at least 80% of wet/dry calls right |

Result: `None` when even day 1 cannot be judged yet, `0` when day 1 fails, otherwise 1 to 7. It is read for the best model.

## Settings

Environment variables, read in `infrastructure/settings.py`. Defaults are the method's.

| Variable | Default | Meaning |
| :--- | :--- | :--- |
| `PRECIPITATION_THRESHOLD_MM` | 0.1 | A day is wet from this much rain |
| `MIN_SAMPLES` | 10 | Scored days needed to rank a model or judge a lead |
| `SCORE_RETENTION_DAYS` | 730 | How long scores are kept, counted back from the latest scored day. At least 365, the longest period the page shows |
| `TRUST_TEMPERATURE_MAE_C` | 2.0 | Temperature bar |
| `TRUST_WIND_MAE_MS` | 1.5 | Wind bar |
| `TRUST_PRESSURE_MAE_HPA` | 2.0 | Pressure bar |
| `TRUST_PRECIPITATION_ACCURACY` | 0.8 | Share of right rain calls |

Changing a threshold changes how new days are scored (the wet threshold) or how stored sums are read (the bars). It does not
rewrite old scores, so changing `PRECIPITATION_THRESHOLD_MM` on a database with history mixes two definitions.

## Limits of the method

Stated so that nobody has to discover them.

1. **Scores lag by about two weeks.** IMGW publishes a month of hourly data after the month ends.
2. **`issued_at` is the fetch time, not the model run time.** Open-Meteo's response does not give the run time. The models
   start a few hours before the fetch, so a "1 day" forecast is slightly fresher than its label. It is the same for every
   model, so rankings are not biased, but absolute lead times are approximate. Forecasts from the archive are stamped with
   midnight UTC of the day `lead` days before, which is the archive's own definition.
3. **The rain Brier score is approximate.** Open-Meteo's `precipitation_probability_max` is the day's highest hourly chance of
   rain, while the event scored is "at least 0.1 mm over the day". The archive has no chance of rain, so history has no
   Brier score.
4. **A station is a point, a model is a grid cell.** Open-Meteo interpolates to the station's coordinates. Mountain stations
   (Zakopane) will score worse for reasons that are not the model's fault.
5. **Wind from IMGW is a whole number of m/s**, so a daily mean has a resolution of about 0.04 m/s and small wind errors are
   noisy.
6. **Pressure is sea-level pressure.** It is missing at Zakopane, where IMGW does not report it.
7. **Small samples are noisy.** Thirty days at one station is a handful of weather situations. The page shows how many days
   a figure rests on and refuses to rank below 10.
8. **Three models are compared, not "the forecast".** Apps, broadcasters and national services post-process model output. A
   good model score does not say how good any of them is.
