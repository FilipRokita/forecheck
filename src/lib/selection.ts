export type Selection = { station: string; variable: string; period: string };

export const DEFAULT_SELECTION: Selection = { station: "12566", variable: "temperature", period: "30d" };

const STORAGE_KEY = "forecheck:selection";
const PARAMS = ["station", "variable", "period"] as const;

type Allowed = { stations: readonly string[]; variables: readonly string[]; periods: readonly string[] };

function sanitize(candidate: Partial<Selection>, allowed: Allowed, fallback: Selection): Selection {
  const pick = (value: string | undefined, options: readonly string[], standard: string) =>
    value !== undefined && options.includes(value) ? value : options.includes(standard) ? standard : (options[0] ?? standard);
  return {
    station: pick(candidate.station, allowed.stations, fallback.station),
    variable: pick(candidate.variable, allowed.variables, fallback.variable),
    period: pick(candidate.period, allowed.periods, fallback.period),
  };
}

/** The selection from the address, else the last one this browser used, else the default. Values the API does not
 * know are replaced, so an old link or stored value can never ask for something that does not exist. */
export function readSelection(search: string, allowed: Allowed): Selection {
  const fromUrl: Partial<Selection> = {};
  const params = new URLSearchParams(search);
  for (const name of PARAMS) {
    const value = params.get(name);
    if (value) fromUrl[name] = value;
  }
  return sanitize({ ...readStored(), ...fromUrl }, allowed, DEFAULT_SELECTION);
}

function readStored(): Partial<Selection> {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : null;
    if (parsed && typeof parsed === "object") {
      const { station, variable, period } = parsed as Record<string, unknown>;
      return {
        ...(typeof station === "string" ? { station } : {}),
        ...(typeof variable === "string" ? { variable } : {}),
        ...(typeof period === "string" ? { period } : {}),
      };
    }
  } catch {
    // Storage can be blocked or hold something else: the page works without it.
  }
  return {};
}

/** Keeps the address shareable and remembers the choice for the next visit. */
export function writeSelection(selection: Selection): void {
  const params = new URLSearchParams(selection);
  window.history.replaceState(null, "", `?${params.toString()}`);
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(selection));
  } catch {
    // Not remembering is fine.
  }
}
