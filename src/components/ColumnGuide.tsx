"use client";

import { useEffect, useRef } from "react";
import { ModelName } from "@/components/ModelName";
import type { Column } from "@/components/RankingTable";
import type { RankedModel, Variable } from "@/lib/api/types";
import { modelColor } from "@/lib/models";

type Props = {
  columns: Column[];
  variable: Variable;
  /** The model ranked first, whose own numbers are used as the examples, and the same model's rain scores. */
  best: RankedModel;
  bestRain: RankedModel | undefined;
};

const BETTER = { lower: "↓ Lower is better", higher: "↑ Higher is better", zero: "◎ Aim for 0" } as const;

/** A button under the ranking that opens a window explaining each column, with the first model's real numbers as examples. */
export function ColumnGuide({ columns, variable, best, bestRain }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    // A press on the backdrop lands on the dialog element itself, not on its content.
    const closeOnBackdrop = (event: MouseEvent) => {
      if (event.target === element) element.close();
    };
    element.addEventListener("click", closeOnBackdrop);
    return () => element.removeEventListener("click", closeOnBackdrop);
  }, []);

  return (
    <>
      <button
        type="button"
        aria-haspopup="dialog"
        onClick={() => dialog.current?.showModal()}
        className="mt-2 flex min-h-11 items-center gap-2 text-fg-muted md:min-h-9 hover:text-fg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-model-ecmwf"
      >
        <span aria-hidden="true" className="grid size-4 place-items-center rounded-full border border-current text-[10px] font-semibold leading-none">
          i
        </span>
        What do these columns mean?
      </button>

      <dialog
        ref={dialog}
        aria-labelledby="column-guide-title"
        className="m-auto max-h-[85dvh] w-[calc(100%-2rem)] max-w-lg overflow-hidden rounded-2xl border border-border bg-surface p-0 text-fg shadow-2xl shadow-black/60 backdrop:bg-black/70 backdrop:backdrop-blur-sm open:animate-fade"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-2">
          <h2 id="column-guide-title" className="text-base font-semibold">
            How to read the ranking
          </h2>
          <button
            type="button"
            aria-label="Close"
            onClick={() => dialog.current?.close()}
            className="grid size-11 place-items-center rounded-lg text-fg-muted hover:bg-surface-raised hover:text-fg focus-visible:outline-2 focus-visible:outline-model-ecmwf sm:size-9"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" aria-hidden="true">
              <path d="M2.5 2.5l9 9M11.5 2.5l-9 9" />
            </svg>
          </button>
        </div>
        <div className="max-h-[calc(85dvh-4rem)] overflow-y-auto px-5 py-4">
          <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-fg-muted">
            Examples are from the model ranked first:
            <span className="rounded-full border border-border-strong bg-surface-raised px-2.5 py-0.5 text-fg">
              <ModelName id={best.model} label={best.label} />
            </span>
          </p>
          <ul className="mt-4 flex flex-col gap-3">
            {columns.map((column) => {
              const value = column.value(best, bestRain) ?? null;
              const unit = column.key === "error" || column.key === "bias" ? variable.unit : "";
              return (
                <li
                  key={column.key}
                  className="rounded-xl border border-border bg-surface-raised/50 p-4 shadow-[inset_0_1px_0_color-mix(in_srgb,var(--color-fg)_6%,transparent)]"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1.5">
                      <h3 className="font-semibold">{column.header}</h3>
                      <span className="rounded-full border border-border-strong px-2 py-0.5 text-[11px] text-fg-muted">{BETTER[column.better]}</span>
                    </div>
                    <div className="text-right font-mono text-2xl font-semibold leading-none" style={{ color: modelColor(best.model) }}>
                      {value === null ? "–" : column.format(value)}
                      {value !== null && unit ? <span className="ml-1 text-sm font-normal text-fg-muted">{unit}</span> : null}
                    </div>
                  </div>
                  <p className="mt-3 text-fg-soft">{column.hint}</p>
                  <Visual column={column} value={value} variable={variable} color={modelColor(best.model)} />
                </li>
              );
            })}
          </ul>
        </div>
      </dialog>
    </>
  );
}

/** A small picture of where a number sits: a bar for shares and errors, a scale with a middle mark for bias. */
function Visual({ column, value, variable, color }: { column: Column; value: number | null; variable: Variable; color: string }) {
  if (value === null) return null;
  if (column.key === "bias") {
    // From "too low" to "too high", with 0 in the middle. The scale reaches as far as the trust limit.
    const position = 50 + Math.max(-1, Math.min(1, value / variable.trust_threshold)) * 45;
    return (
      <div className="mt-3" aria-hidden="true">
        <div className="relative h-1.5 rounded-full bg-surface-raised">
          <div className="absolute left-1/2 top-1/2 h-3 w-px -translate-y-1/2 bg-fg-muted" />
          <div className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface" style={{ left: `${position}%`, background: color }} />
        </div>
        <div className="mt-1 flex justify-between text-[11px] text-fg-muted">
          <span>too low</span>
          <span>0</span>
          <span>too high</span>
        </div>
      </div>
    );
  }
  if (column.key === "error") {
    // The bar runs to 1.5 times the trust limit, and the dashed mark is the limit itself.
    const reach = variable.trust_threshold * 1.5;
    return (
      <div className="mt-3" aria-hidden="true">
        <div className="relative h-1.5 rounded-full bg-surface-raised">
          <div className="h-full rounded-full" style={{ width: `${Math.min(value / reach, 1) * 100}%`, background: color }} />
          <div className="absolute top-1/2 h-3 border-l border-dashed border-fg-soft" style={{ left: `${(1 / 1.5) * 100}%`, transform: "translateY(-50%)" }} />
        </div>
        <div className="mt-1 flex justify-between text-[11px] text-fg-muted">
          <span>0</span>
          <span>limit {variable.trust_threshold} {variable.unit}</span>
        </div>
      </div>
    );
  }
  // Shares and the Brier score both run from 0 to 1.
  return (
    <div className="mt-3" aria-hidden="true">
      <div className="h-1.5 rounded-full bg-surface-raised">
        <div className="h-full rounded-full" style={{ width: `${Math.max(0, Math.min(value, 1)) * 100}%`, background: color }} />
      </div>
      <div className="mt-1 flex justify-between text-[11px] text-fg-muted">
        <span>0</span>
        <span>{column.key === "brier" ? "1" : "100%"}</span>
      </div>
    </div>
  );
}
