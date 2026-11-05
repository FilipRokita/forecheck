import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Dashboard } from "@/components/Dashboard";
import { accessibilityViolations } from "@/test/axe";
import { comparison, horizon, meta, rainVerdict, verdict } from "@/test/fixtures";

type Handler = (url: URL) => unknown;

/** A stand-in for the API: answers by path, and records what was asked. */
function serve(overrides: Record<string, Handler> = {}) {
  const asked: string[] = [];
  const handlers: Record<string, Handler> = {
    "/api/meta": () => meta(),
    "/api/stations/12566/verdict": (url) => (url.searchParams.get("variable") === "precipitation" ? rainVerdict() : verdict()),
    "/api/stations/12566/horizon": () => horizon(),
    "/api/stations/12580/verdict": (url) =>
      url.searchParams.get("variable") === "precipitation" ? rainVerdict() : verdict({ station: { ...verdict().station, id: "12580", name: "Rzeszów" } }),
    "/api/stations/12580/horizon": () => horizon(),
    "/api/comparison": () => comparison(),
    ...overrides,
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string) => {
      const url = new URL(input, "http://localhost");
      asked.push(`${url.pathname}${url.search}`);
      const handler = handlers[url.pathname];
      if (!handler) return new Response("not found", { status: 404 });
      return new Response(JSON.stringify(handler(url)), { status: 200, headers: { "content-type": "application/json" } });
    }),
  );
  return asked;
}

beforeEach(() => {
  window.localStorage.clear();
  window.history.replaceState(null, "", "/");
});
afterEach(() => vi.unstubAllGlobals());

describe("Dashboard", () => {
  it("shows the verdict, the chart, the ranking and the comparison for the chosen station", async () => {
    serve();
    render(<Dashboard />);
    expect(await screen.findByText("Most accurate model", { exact: false })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Temperature error by forecast horizon" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Model ranking" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Station comparison" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Forecheck" })).toBeInTheDocument();
    expect(screen.getByText("Scored through")).toBeInTheDocument();
  });

  it("asks for what the address says", async () => {
    window.history.replaceState(null, "", "/?station=12580&variable=precipitation&period=90d");
    const asked = serve();
    render(<Dashboard />);
    await screen.findByText("Rain tomorrow");
    expect(asked).toContain("/api/stations/12580/verdict?variable=precipitation&period=90d");
    expect(asked).toContain("/api/comparison?variable=precipitation&period=90d&lead_days=1");
  });

  it("changes the quantity, updates the address and fetches again", async () => {
    const asked = serve();
    render(<Dashboard />);
    await screen.findByText("Rain tomorrow");
    await userEvent.click(screen.getByRole("button", { name: "Precipitation" }));
    await waitFor(() => expect(window.location.search).toContain("variable=precipitation"));
    expect(asked).toContain("/api/stations/12566/horizon?variable=precipitation&period=30d");
    expect(screen.getByRole("button", { name: "Precipitation" })).toHaveAttribute("aria-pressed", "true");
  });

  it("opens another station from the comparison", async () => {
    serve();
    render(<Dashboard />);
    await screen.findByText("Rain tomorrow");
    await userEvent.click(within(screen.getByRole("table", { name: /Best model/ })).getByRole("button", { name: "Rzeszów" }));
    await waitFor(() => expect(window.location.search).toContain("station=12580"));
    expect(window.localStorage.getItem("forecheck:selection")).toContain("12580");
  });

  it("links the CSV export to what is on screen", async () => {
    serve();
    render(<Dashboard />);
    await screen.findByText("Rain tomorrow");
    expect(screen.getByRole("link", { name: "Export CSV" })).toHaveAttribute("href", "/api/stations/12566/export.csv?variable=temperature&period=30d");
  });

  it("flags sample data", async () => {
    serve({ "/api/meta": () => meta({ status: { sample_data: true, latest_scored_day: "2026-09-30", waiting_forecasts: 0, last_runs: [] } }) });
    render(<Dashboard />);
    expect(await screen.findByText("Sample data")).toBeInTheDocument();
  });

  it("flags a window that is not full yet", async () => {
    serve({ "/api/stations/12566/verdict": () => verdict({ scored_days: 12 }) });
    render(<Dashboard />);
    expect(await screen.findByText("Limited history: 12 scored days")).toBeInTheDocument();
  });

  it("explains an empty database instead of showing zeros", async () => {
    serve({
      "/api/meta": () => meta({ status: { sample_data: false, latest_scored_day: null, waiting_forecasts: 0, last_runs: [] } }),
      "/api/stations/12566/verdict": () => verdict({ best_model: null, best_model_label: null, trust_days: null, next_day: null, ranking: [], scored_days: 0, window: null }),
      "/api/stations/12566/horizon": () => horizon({ models: [], window: null }),
      "/api/comparison": () => comparison({ rows: [], window: null }),
    });
    render(<Dashboard />);
    expect(await screen.findByText(/Nothing is scored yet/)).toBeInTheDocument();
    expect(screen.getByText("Too early")).toBeInTheDocument();
  });

  it("offers a retry when the API fails", async () => {
    let fail = true;
    serve({
      "/api/meta": () => {
        if (fail) throw new Error("down");
        return meta();
      },
    });
    // The stand-in turns a throwing handler into a rejected fetch.
    const original = globalThis.fetch;
    vi.stubGlobal("fetch", async (input: string) => (fail ? new Response("nope", { status: 503 }) : original(input)));
    render(<Dashboard />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load the app.");
    fail = false;
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { name: "Model ranking" })).toBeInTheDocument();
  });

  it("has no structural accessibility violations", async () => {
    serve();
    const { container } = render(<Dashboard />);
    await screen.findByText("Rain tomorrow");
    expect(await accessibilityViolations(container)).toEqual([]);
  });

  it("still shows the verdict when only the rain request fails", async () => {
    serve({
      "/api/stations/12566/verdict": (url) => {
        if (url.searchParams.get("variable") === "precipitation") throw new Error("boom");
        return verdict();
      },
    });
    render(<Dashboard />);
    expect(await screen.findByText("Most accurate model", { exact: false })).toBeInTheDocument();
    expect(await screen.findByText("Could not load rain scores.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Model ranking" })).toBeInTheDocument();
  });
});
