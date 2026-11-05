"use client";

import { useState } from "react";
import { Async } from "@/components/Async";
import { Badge } from "@/components/Badge";
import { CountUpInt } from "@/components/CountUp";
import { Footer } from "@/components/Footer";
import { Headline } from "@/components/Headline";
import { HorizonChart } from "@/components/HorizonChart";
import { Logo } from "@/components/Logo";
import { RankingTable } from "@/components/RankingTable";
import { SegmentedControl } from "@/components/SegmentedControl";
import { StationComparison } from "@/components/StationComparison";
import { StationPicker } from "@/components/StationPicker";
import { VerdictCards } from "@/components/VerdictCards";
import { api } from "@/lib/api/client";
import type { Meta } from "@/lib/api/types";
import { useApi } from "@/lib/api/use-api";
import { formatDay } from "@/lib/format";
import { REPOSITORY } from "@/lib/links";
import { readSelection, type Selection, writeSelection } from "@/lib/selection";

/** Every answer stays on screen, marked stale, until the next one arrives, so a change of selection never blanks the page. */
const KEEP = "keep";

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

  const verdict = useApi(`verdict|${key}`, (signal) => api.verdict(stationId, variableId, periodId, signal), KEEP);
  const rain = useApi(`rain|${stationId}|${periodId}`, (signal) => api.verdict(stationId, rainVariable?.id ?? "precipitation", periodId, signal), KEEP);
  const horizon = useApi(`horizon|${key}`, (signal) => api.horizon(stationId, variableId, periodId, signal), KEEP);
  const comparison = useApi(`comparison|${variableId}|${periodId}`, (signal) => api.comparison(variableId, periodId, 1, signal), KEEP);

  if (!variable || !period || !rainVariable) return null;
  const { status } = meta;
  const updating = [verdict, rain, horizon, comparison].some((state) => state.status === "ready" && state.stale);
  // What is on screen may still belong to the previous selection, so each part is written in the unit and for the period
  // of its own answer, never of the current choice.
  const variableOf = (id: string) => meta.variables.find((v) => v.id === id) ?? variable;
  const periodOf = (id: string) => meta.periods.find((p) => p.id === id) ?? period;

  return (
    <>
      <header className="z-20 border-b border-border bg-bg/80 sticky top-0 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1280px] flex-wrap items-center justify-between gap-4 px-4 py-3 sm:px-10 sm:py-2.5">
          <h1>
            <Logo />
          </h1>
          <div className="ml-auto flex items-center gap-1.5 sm:gap-3">
            {status.sample_data ? <Badge>Sample data</Badge> : null}
            <a
              href={api.exportUrl(stationId, variableId, periodId)}
              download
              className="flex min-h-11 items-center gap-2 rounded-[10px] border border-border-strong px-3.5 text-sm sm:min-h-9 max-sm:w-11 max-sm:justify-center max-sm:px-0 hover:bg-surface focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-model-ecmwf"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M8 2.5v8M4.5 7.5L8 11l3.5-3.5M3 13.5h10" />
              </svg>
              <span className="max-sm:sr-only">Export CSV</span>
            </a>
            <a
              href={REPOSITORY}
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Forecheck on GitHub"
              className="flex size-11 items-center justify-center rounded-[10px] text-fg-muted hover:bg-surface hover:text-fg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-model-ecmwf sm:size-9"
            >
              <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
              </svg>
            </a>
          </div>
        </div>
        {updating ? (
          // Appears only if the answer takes a moment, so a quick change shows no flicker.
          <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 bottom-0 h-0.5 animate-fade overflow-hidden" style={{ animationDelay: "250ms" }}>
            <div className="h-full w-1/3 animate-slide bg-model-ecmwf" />
          </div>
        ) : null}
      </header>

      <div className="mx-auto flex max-w-[1280px] flex-col gap-3 px-4 py-4 sm:flex-row sm:flex-wrap sm:items-end sm:gap-x-6 sm:gap-y-3 sm:px-10 sm:py-5">
        <StationPicker stations={meta.stations} value={stationId} onChange={(id) => choose({ station: id })} />
        <SegmentedControl label="Quantity" options={meta.variables} value={variableId} onChange={(id) => choose({ variable: id })} scroll />
        <SegmentedControl label="Period" options={meta.periods} value={periodId} onChange={(id) => choose({ period: id })} />
      </div>

      <main aria-busy={updating} className="mx-auto flex max-w-[1280px] flex-col gap-3 px-4 pb-10 pt-3 sm:gap-4 sm:px-10 sm:pt-4">
        <Async state={verdict} label="the verdict" skeletonClassName="h-48">
          {(v) => (
            <>
              <Headline variable={variableOf(v.variable)} verdict={v} />
              <FreshnessNote latest={status.latest_scored_day} scoredDays={v.scored_days} windowDays={periodOf(v.period).days} />
              <VerdictCards variable={variableOf(v.variable)} period={periodOf(v.period)} verdict={v} rain={rain} wetThresholdMm={meta.precipitation_threshold_mm} />
            </>
          )}
        </Async>

        <div className="flex flex-wrap gap-3 sm:gap-4">
          <Async state={horizon} label="the chart" skeletonClassName="h-72 flex-[3_1_34rem]">
            {(h) => <HorizonChart horizon={h} variable={variableOf(h.variable)} periodLabel={periodOf(h.period).label} />}
          </Async>
          <Async state={verdict} label="the ranking" skeletonClassName="h-72 flex-[2_1_22rem]">
            {(v) => (
              <RankingTable
                variable={variableOf(v.variable)}
                verdict={v}
                rain={rain.status === "ready" && rain.data.station.id === v.station.id && rain.data.period === v.period ? rain.data : undefined}
              />
            )}
          </Async>
        </div>

        <Async state={comparison} label="the station comparison" skeletonClassName="h-80">
          {(c) => <StationComparison comparison={c} variable={variableOf(c.variable)} period={periodOf(c.period)} selectedStation={stationId} />}
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
  // The row is as tall as the badge even without it, so the page does not shift when the badge comes and goes.
  return (
    <p className="flex min-h-[26px] flex-wrap items-center gap-x-3 gap-y-2 text-fg-muted">
      <span>
        Scored through <span className="text-fg">{formatDay(latest)}</span>
      </span>
      {limited ? <Badge>
          Limited history: <CountUpInt value={scoredDays} /> scored days
        </Badge> : null}
    </p>
  );
}
