import type { Comparison, Figure, Horizon, Meta, RankedModel, Station, Variable, Verdict } from "@/lib/api/types";

export const KRAKOW: Station = { id: "12566", name: "Kraków", latitude: 50.078, longitude: 19.785 };
export const RZESZOW: Station = { id: "12580", name: "Rzeszów", latitude: 50.11, longitude: 22.019 };

export const TEMPERATURE: Variable = { id: "temperature", label: "Temperature", unit: "°C", metric: "mae", trust_threshold: 2 };
export const PRECIPITATION: Variable = { id: "precipitation", label: "Precipitation", unit: "mm", metric: "accuracy", trust_threshold: 0.8 };

export const PERIOD_30 = { id: "30d", label: "30 days", days: 30 };

export function figure(over: Partial<Figure> = {}): Figure {
  return { n: 30, mae: 1.3, bias: -0.2, rmse: 1.6, accuracy: null, hit_rate: null, false_alarm_ratio: null, brier: null, ...over };
}

export function ranked(model: string, label: string, rank: number | null, over: Partial<Figure> = {}): RankedModel {
  return { model, label, rank, ...figure(over) };
}

export function verdict(over: Partial<Verdict> = {}): Verdict {
  return {
    station: KRAKOW,
    variable: "temperature",
    period: "30d",
    window: { start: "2026-09-01", end: "2026-09-30" },
    lead_from: 1,
    lead_to: 3,
    best_model: "ecmwf",
    best_model_label: "ECMWF",
    trust_days: 3,
    next_day: figure({ n: 30, mae: 0.9 }),
    scored_days: 30,
    ranking: [
      ranked("ecmwf", "ECMWF", 1, { mae: 1.3 }),
      ranked("icon", "ICON", 2, { mae: 1.4 }),
      ranked("gfs", "GFS", 3, { mae: 1.8 }),
    ],
    ...over,
  };
}

export function rainVerdict(over: Partial<Verdict> = {}): Verdict {
  const wet = { mae: 0.4, accuracy: 0.81, hit_rate: 0.7, false_alarm_ratio: 0.2, brier: 0.14 };
  return verdict({
    variable: "precipitation",
    next_day: figure({ ...wet }),
    ranking: [ranked("ecmwf", "ECMWF", 1, wet), ranked("icon", "ICON", 2, { ...wet, accuracy: 0.79, brier: 0.15 }), ranked("gfs", "GFS", 3, { ...wet, accuracy: 0.74, brier: 0.19 })],
    ...over,
  });
}

export function horizon(over: Partial<Horizon> = {}): Horizon {
  const leads = (base: number) => [1, 2, 3, 4, 5, 6, 7].map((lead) => ({ lead_days: lead, ...figure({ mae: base + lead * 0.3 }) }));
  return {
    station: KRAKOW,
    variable: "temperature",
    period: "30d",
    window: { start: "2026-09-01", end: "2026-09-30" },
    metric: "mae",
    trust_threshold: 2,
    models: [
      { model: "icon", label: "ICON", leads: leads(0.8) },
      { model: "ecmwf", label: "ECMWF", leads: leads(0.7) },
      { model: "gfs", label: "GFS", leads: leads(1.0) },
    ],
    ...over,
  };
}

export function comparison(over: Partial<Comparison> = {}): Comparison {
  return {
    variable: "temperature",
    period: "30d",
    lead_days: 1,
    window: { start: "2026-09-01", end: "2026-09-30" },
    metric: "mae",
    rows: [
      { station: KRAKOW, best_model: "ecmwf", best_model_label: "ECMWF", figures: figure({ mae: 1.0 }) },
      { station: RZESZOW, best_model: null, best_model_label: null, figures: null },
    ],
    ...over,
  };
}

export function meta(over: Partial<Meta> = {}): Meta {
  return {
    stations: [KRAKOW, RZESZOW],
    models: [
      { id: "icon", label: "ICON" },
      { id: "ecmwf", label: "ECMWF" },
      { id: "gfs", label: "GFS" },
    ],
    variables: [TEMPERATURE, PRECIPITATION],
    periods: [PERIOD_30, { id: "90d", label: "90 days", days: 90 }],
    min_samples: 10,
    precipitation_threshold_mm: 0.1,
    ranking_lead_max: 3,
    attribution: {
      open_meteo: "Weather data by Open-Meteo.com",
      open_meteo_url: "https://open-meteo.com/",
      open_meteo_licence: "CC BY 4.0",
      imgw_source: "x",
      imgw_processed: "y",
      imgw_url: "https://danepubliczne.imgw.pl/",
    },
    status: { sample_data: false, latest_scored_day: "2026-09-30", waiting_forecasts: 100, last_runs: [] },
    ...over,
  };
}
