"use client";

import { useState } from "react";
import { Async } from "@/components/Async";
import { Badge } from "@/components/Badge";
import { Footer } from "@/components/Footer";
import { Headline } from "@/components/Headline";
import { HorizonChart } from "@/components/HorizonChart";
import { RankingTable } from "@/components/RankingTable";
import { SegmentedControl } from "@/components/SegmentedControl";
import { StationComparison } from "@/components/StationComparison";
import { StationPicker } from "@/components/StationPicker";
import { VerdictCards } from "@/components/VerdictCards";
import { api } from "@/lib/api/client";
import type { Meta } from "@/lib/api/types";
import { useApi } from "@/lib/api/use-api";
import { formatDay } from "@/lib/format";
import { readSelection, type Selection, writeSelection } from "@/lib/selection";

export function Dashboard() {
  const meta = useApi("meta", (signal) => api.meta(signal));
  return (
    <div className="min-h-dvh">
      <Async state={meta} label="the app" skeletonClassName="m-4 h-96">
        {(loaded) => <Loaded meta={loaded} />}
      </Async>
    </div>
  );
}

function Loaded({ meta }: { meta: Meta }) {
  // This component only renders in the browser (the metadata is fetched there), so reading the address is safe.
  const [selection, setSelection] = useState<Selection>(() =>
    readSelection(window.location.search, {
      stations: meta.stations.map((s) => s.id),
      variables: meta.variables.map((v) => v.id),
      periods: meta.periods.map((p) => p.id),
    }),
  );
  const choose = (patch: Partial<Selection>) => {
    const next = { ...selection, ...patch };
    setSelection(next);
    writeSelection(next);
  };

  const { station: stationId, variable: variableId, period: periodId } = selection;
  const variable = meta.variables.find((v) => v.id === variableId) ?? meta.variables[0];
  const period = meta.periods.find((p) => p.id === periodId) ?? meta.periods[0];
  const rainVariable = meta.variables.find((v) => v.metric === "accuracy");
  const key = `${stationId}|${variableId}|${periodId}`;

  const verdict = useApi(`verdict|${key}`, (signal) => api.verdict(stationId, variableId, periodId, signal), `${variableId}|${periodId}`);
  const rain = useApi(`rain|${stationId}|${periodId}`, (signal) => api.verdict(stationId, rainVariable?.id ?? "precipitation", periodId, signal), periodId);
  const horizon = useApi(`horizon|${key}`, (signal) => api.horizon(stationId, variableId, periodId, signal), `${variableId}|${periodId}`);
  const comparison = useApi(`comparison|${variableId}|${periodId}`, (signal) => api.comparison(variableId, periodId, 1, signal));

  if (!variable || !period || !rainVariable) return null;
  const { status } = meta;
  // A new station is loading while the old one's figures, which name it, stay on screen but dimmed.
  const updating = [verdict, rain, horizon].some((state) => state.status === "ready" && state.stale);

  return (
    <>
      <header className="z-20 flex flex-wrap items-center justify-between gap-4 border-b border-border bg-bg/80 px-4 py-4 backdrop-blur-md sm:sticky sm:top-0 sm:px-10 sm:py-5">
        <div className="flex items-center gap-x-2.5">
          <div aria-hidden="true" className="flex size-6 flex-none items-center justify-center rounded-md border border-border-strong bg-surface">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="var(--color-model-ecmwf)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 8.5l3.2 3L13 4.5" />
            </svg>
          </div>
          <div className="flex items-baseline gap-x-3">
            <h1 className="text-[15px] font-semibold leading-none tracking-tight">Forecheck</h1>
            <p className="text-[13px] leading-none text-fg-muted max-sm:hidden">How far can you trust a weather forecast?</p>
          </div>
        </div>
        <div className="ml-auto flex items-center gap-3">
          {status.sample_data ? <Badge>Sample data</Badge> : null}
          <a
            href={api.exportUrl(stationId, variableId, periodId)}
            download
            className="flex min-h-11 items-center gap-2 rounded-[10px] border border-border-strong px-3.5 text-sm max-sm:w-11 max-sm:justify-center max-sm:px-0 hover:bg-surface focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-model-ecmwf"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M8 2.5v8M4.5 7.5L8 11l3.5-3.5M3 13.5h10" />
            </svg>
            <span className="max-sm:sr-only">Export CSV</span>
          </a>
        </div>
      </header>

      <div className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-6 sm:gap-y-3 sm:px-10 sm:py-5">
        <StationPicker stations={meta.stations} value={stationId} onChange={(id) => choose({ station: id })} />
        <SegmentedControl label="Quantity" options={meta.variables} value={variableId} onChange={(id) => choose({ variable: id })} scroll />
        <SegmentedControl label="Period" options={meta.periods} value={periodId} onChange={(id) => choose({ period: id })} />
      </div>

      <main aria-busy={updating} className={`mx-auto flex max-w-[1280px] flex-col gap-3 px-4 pb-10 pt-2 transition-opacity duration-200 sm:gap-4 sm:px-10 ${updating ? "opacity-50" : ""}`}>
        <Async state={verdict} label="the verdict" skeletonClassName="h-48">
          {(v) => (
            <>
              <Headline variable={variable} verdict={v} />
              <FreshnessNote latest={status.latest_scored_day} scoredDays={v.scored_days} windowDays={period.days} />
              <VerdictCards variable={variable} period={period} verdict={v} rain={rain} wetThresholdMm={meta.precipitation_threshold_mm} />
            </>
          )}
        </Async>

        <div className="flex flex-wrap gap-3 sm:gap-4">
          <Async state={horizon} label="the chart" skeletonClassName="h-72 flex-[3_1_34rem]">
            {(h) => <HorizonChart horizon={h} variable={variable} periodLabel={period.label} />}
          </Async>
          <Async state={verdict} label="the ranking" skeletonClassName="h-72 flex-[2_1_22rem]">
            {(v) => <RankingTable variable={variable} verdict={v} rain={rain.status === "ready" ? rain.data : undefined} />}
          </Async>
        </div>

        <Async state={comparison} label="the station comparison" skeletonClassName="h-80">
          {(c) => <StationComparison comparison={c} variable={variable} period={period} selectedStation={stationId} onSelect={(id) => choose({ station: id })} />}
        </Async>

        <Footer />
      </main>
    </>
  );
}

function FreshnessNote({ latest, scoredDays, windowDays }: { latest: string | null | undefined; scoredDays: number; windowDays: number }) {
  if (!latest) {
    return (
      <p className="text-fg-muted" role="status">
        Nothing is scored yet. Forecasts are collected every day and scored once IMGW publishes the month they were about.
      </p>
    );
  }
  const limited = scoredDays < windowDays;
  return (
    <p className="flex flex-wrap items-center gap-x-3 gap-y-2 text-fg-muted">
      <span>
        Scored through <span className="text-fg">{formatDay(latest)}</span>
      </span>
      {limited ? <Badge>Limited history: {scoredDays} scored days</Badge> : null}
    </p>
  );
}
