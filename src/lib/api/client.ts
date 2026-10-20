import type { Comparison, Horizon, Meta, Verdict } from "./types";

/** The API shares the page's origin (`/api/...`); an override exists for a separately hosted API. */
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${BASE}${path}`, { signal, headers: { Accept: "application/json" } });
  if (!response.ok) throw new ApiError(`The server answered ${response.status}`, response.status);
  return (await response.json()) as T;
}

function query(params: Record<string, string | number>): string {
  return new URLSearchParams(Object.entries(params).map(([key, value]) => [key, String(value)])).toString();
}

export const api = {
  meta: (signal?: AbortSignal) => getJson<Meta>("/api/meta", signal),
  verdict: (station: string, variable: string, period: string, signal?: AbortSignal) =>
    getJson<Verdict>(`/api/stations/${encodeURIComponent(station)}/verdict?${query({ variable, period })}`, signal),
  horizon: (station: string, variable: string, period: string, signal?: AbortSignal) =>
    getJson<Horizon>(`/api/stations/${encodeURIComponent(station)}/horizon?${query({ variable, period })}`, signal),
  comparison: (variable: string, period: string, lead: number, signal?: AbortSignal) =>
    getJson<Comparison>(`/api/comparison?${query({ variable, period, lead_days: lead })}`, signal),
  exportUrl: (station: string, variable: string, period: string) =>
    `${BASE}/api/stations/${encodeURIComponent(station)}/export.csv?${query({ variable, period })}`,
};
