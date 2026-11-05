"use client";

import { useEffect, useRef } from "react";
import type { Station } from "@/lib/api/types";

type Props = {
  stations: readonly Station[];
  value: string;
  onChange: (id: string) => void;
};

/** A button that opens a modal list of stations: a bottom sheet on a phone, a centred panel on a desktop. */
export function StationPicker({ stations, value, onChange }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const current = stations.find((station) => station.id === value);

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    // A click on the backdrop lands on the dialog element itself, not on its content.
    const closeOnBackdrop = (event: MouseEvent) => {
      if (event.target === element) element.close();
    };
    element.addEventListener("click", closeOnBackdrop);
    return () => element.removeEventListener("click", closeOnBackdrop);
  }, []);

  return (
    <div className="flex flex-col gap-1.5">
      <span id="station-label" className="text-xs text-fg-muted max-sm:sr-only">
        IMGW station
      </span>
      <button
        ref={opener}
        aria-labelledby="station-label station-value"
        type="button"
        aria-haspopup="dialog"
        onClick={() => dialog.current?.showModal()}
        className="flex min-h-12 w-full items-center justify-between gap-3 rounded-xl border border-border bg-surface px-4 text-left text-base hover:border-border-strong hover:bg-surface-raised focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-model-ecmwf sm:min-h-[46px] sm:w-auto sm:min-w-64 sm:rounded-[10px] sm:text-sm"
      >
        <span id="station-value" className="font-medium">
          {current?.name ?? "Choose a station"}
        </span>
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="text-fg-muted">
          <path d="M3.5 5.5L7 9l3.5-3.5" />
        </svg>
      </button>

      <dialog
        ref={dialog}
        aria-labelledby="station-dialog-title"
        className="m-0 mt-auto max-h-[85dvh] w-full max-w-none overflow-hidden rounded-t-2xl border border-border bg-surface p-0 text-fg backdrop:bg-black/70 backdrop:backdrop-blur-sm open:animate-sheet sm:m-auto sm:max-h-[70dvh] sm:max-w-md sm:rounded-2xl"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-3">
          <h2 id="station-dialog-title" className="text-base font-semibold">
            Choose a station
          </h2>
          <button type="button" onClick={() => dialog.current?.close()} className="min-h-11 rounded-lg px-3 text-fg-muted hover:text-fg focus-visible:outline-2 focus-visible:outline-model-ecmwf">
            Close
          </button>
        </div>
        <ul className="max-h-[calc(85dvh-4rem)] overflow-y-auto p-2 sm:max-h-[calc(70dvh-4rem)]">
          {stations.map((station) => {
            const selected = station.id === value;
            return (
              <li key={station.id}>
                <button
                  type="button"
                  aria-current={selected ? "true" : undefined}
                  onClick={() => {
                    onChange(station.id);
                    dialog.current?.close();
                    opener.current?.focus();
                  }}
                  className={`flex min-h-12 w-full items-center justify-between rounded-lg px-4 text-left text-base focus-visible:outline-2 focus-visible:outline-model-ecmwf sm:text-sm ${
                    selected ? "bg-surface-raised font-medium text-white" : "text-fg hover:bg-surface-raised hover:pl-5"
                  }`}
                >
                  <span>{station.name}</span>
                  {selected ? <span className="text-xs text-model-ecmwf">Selected</span> : null}
                </button>
              </li>
            );
          })}
        </ul>
      </dialog>
    </div>
  );
}
