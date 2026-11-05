"use client";

import { useState } from "react";
import { Sheet } from "@/components/Sheet";
import type { Selection } from "@/lib/selection";

type Option = { id: string; label: string };

type Props = {
  stations: readonly { id: string; name: string }[];
  variables: readonly Option[];
  periods: readonly Option[];
  selection: Selection;
  onChange: (patch: Partial<Selection>) => void;
};

/**
 * On a phone, the three controls would fill the first screen. Here they are one button that shows what is chosen and opens
 * a drawer with all three. A choice applies at once, so the page behind the drawer is already changing.
 */
export function SelectionDrawer({ stations, variables, periods, selection, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const station = stations.find((s) => s.id === selection.station)?.name ?? "Station";
  const variable = variables.find((v) => v.id === selection.variable)?.label ?? "";
  const period = periods.find((p) => p.id === selection.period)?.label ?? "";

  return (
    <div className="sm:hidden">
      <button
        type="button"
        aria-haspopup="dialog"
        aria-label={`Configure: ${station}, ${variable}, ${period}`}
        onClick={() => setOpen(true)}
        className="flex min-h-12 w-full items-center justify-between gap-3 rounded-xl border border-border bg-surface px-4 text-left text-base hover:border-border-strong hover:bg-surface-raised focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-model-ecmwf"
      >
        <span className="flex min-w-0 items-center gap-3">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" aria-hidden="true" className="flex-none text-fg-muted">
            <path d="M2.5 5h6M12.5 5h3M2.5 13h3M9.5 13h6" />
            <circle cx="10.5" cy="5" r="1.8" />
            <circle cx="7.5" cy="13" r="1.8" />
          </svg>
          <span className="min-w-0 truncate" aria-hidden="true">
            <span className="font-medium">{station}</span>
            <span className="text-fg-muted">
              {" "}
              · {variable} · {period}
            </span>
          </span>
        </span>
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="flex-none text-fg-muted">
          <path d="M3.5 8.5L7 5l3.5 3.5" />
        </svg>
      </button>

      <Sheet title="Configure" open={open} onClose={() => setOpen(false)}>
        <div className="flex flex-col gap-5">
          <Choice label="Station" options={stations.map((s) => ({ id: s.id, label: s.name }))} value={selection.station} onChange={(id) => onChange({ station: id })} />
          <Choice label="Quantity" options={variables} value={selection.variable} onChange={(id) => onChange({ variable: id })} />
          <Choice label="Period" options={periods} value={selection.period} onChange={(id) => onChange({ period: id })} />
        </div>
        <button
          type="button"
          data-sheet-close
          className="mt-6 min-h-12 w-full rounded-xl border border-border-strong bg-surface-raised font-medium hover:bg-border focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-model-ecmwf"
        >
          Done
        </button>
      </Sheet>
    </div>
  );
}

function Choice({ label, options, value, onChange }: { label: string; options: readonly Option[]; value: string; onChange: (id: string) => void }) {
  const id = `choice-${label}`;
  return (
    <section>
      <h3 id={id} className="text-xs uppercase tracking-[0.06em] text-fg-muted">
        {label}
      </h3>
      <div role="group" aria-labelledby={id} className="mt-2 flex flex-wrap gap-2">
        {options.map((option) => {
          const selected = option.id === value;
          return (
            <button
              key={option.id}
              type="button"
              aria-pressed={selected}
              onClick={() => onChange(option.id)}
              className={`min-h-11 rounded-lg border px-4 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-model-ecmwf ${
                selected ? "border-border-strong bg-surface-raised font-medium text-white" : "border-border text-fg-muted hover:bg-surface-raised/60 hover:text-fg"
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </section>
  );
}
