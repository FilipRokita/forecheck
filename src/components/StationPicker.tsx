"use client";

import { useEffect, useId, useRef, useState } from "react";
import type { Station } from "@/lib/api/types";

type Props = {
  stations: readonly Station[];
  value: string;
  onChange: (id: string) => void;
};

/** Lower case without accents, so "lodz" finds "Łódź". (ł has no decomposition, so it is mapped by hand.) */
function fold(text: string): string {
  return text.toLowerCase().replace(/ł/g, "l").normalize("NFD").replace(/\p{M}/gu, "");
}

/** A dropdown under its button: a search box on top, the matching stations below. Arrow keys and Enter work from the box. */
export function StationPicker({ stations, value, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const prefix = useId();
  const listId = `${prefix}-list`;
  const optionId = (id: string) => `${prefix}-${id}`;

  const current = stations.find((station) => station.id === value);
  const needle = fold(query.trim());
  const shown = stations.filter((station) => fold(station.name).includes(needle));

  const close = (returnFocus: boolean) => {
    setOpen(false);
    setQuery("");
    if (returnFocus) opener.current?.focus();
  };
  const choose = (id: string) => {
    onChange(id);
    close(true);
  };
  const toggle = () => {
    if (open) return close(false);
    setActive(Math.max(0, stations.findIndex((station) => station.id === value)));
    setOpen(true);
  };

  useEffect(() => {
    if (!open) return;
    // A phone's keyboard would cover the list, so only a pointer device gets the cursor in the box at once.
    if (!window.matchMedia?.("(pointer: coarse)").matches) search.current?.focus();
    const closeOnOutsideClick = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) {
        setOpen(false);
        setQuery("");
      }
    };
    document.addEventListener("pointerdown", closeOnOutsideClick);
    return () => document.removeEventListener("pointerdown", closeOnOutsideClick);
  }, [open]);

  const activeStation = shown[active];
  useEffect(() => {
    if (open && activeStation) document.getElementById(optionId(activeStation.id))?.scrollIntoView?.({ block: "nearest" });
    // optionId only depends on `prefix`, which never changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, activeStation?.id]);

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((index) => Math.min(index + 1, shown.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((index) => Math.max(index - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (activeStation) choose(activeStation.id);
    } else if (event.key === "Escape") {
      event.preventDefault();
      close(true);
    }
  };

  return (
    <div
      ref={root}
      className="relative flex flex-col gap-1.5"
      onBlur={(event) => {
        // Tabbing out of the dropdown closes it.
        if (open && !event.currentTarget.contains(event.relatedTarget)) close(false);
      }}
    >
      <span id={`${prefix}-label`} className="text-xs text-fg-muted max-sm:sr-only">
        IMGW station
      </span>
      <button
        ref={opener}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        aria-labelledby={`${prefix}-label ${prefix}-value`}
        onClick={toggle}
        className={`flex min-h-12 w-full active:transform-none items-center justify-between gap-3 border px-4 text-left text-base hover:border-border-strong hover:bg-surface-raised focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-model-ecmwf sm:min-h-[46px] sm:w-auto sm:min-w-64 sm:text-sm ${
          open ? "rounded-t-xl rounded-b-none border-border-strong bg-surface-raised sm:rounded-t-[10px]" : "rounded-xl border-border bg-surface sm:rounded-[10px]"
        }`}
      >
        <span id={`${prefix}-value`} className="font-medium">
          {current?.name ?? "Choose a station"}
        </span>
        <svg
          width="14"
          height="14"
          viewBox="0 0 14 14"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          className={`text-fg-muted transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        >
          <path d="M3.5 5.5L7 9l3.5-3.5" />
        </svg>
      </button>

      {open ? (
        <div className="absolute left-0 top-full z-30 w-full min-w-64 overflow-hidden rounded-b-xl border border-t-0 border-border-strong bg-surface shadow-2xl shadow-black/60 sm:rounded-b-[10px]">
          <div className="border-b border-border p-2">
            <input
              ref={search}
              type="text"
              role="combobox"
              aria-expanded="true"
              aria-controls={listId}
              aria-autocomplete="list"
              aria-activedescendant={activeStation ? optionId(activeStation.id) : undefined}
              aria-label="Search stations"
              placeholder="Search stations"
              autoComplete="off"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setActive(0);
              }}
              onKeyDown={onKeyDown}
              className="h-10 w-full rounded-lg border border-transparent bg-surface-raised px-3 text-base placeholder:text-fg-muted focus-visible:border-model-ecmwf focus-visible:outline-none sm:text-sm"
            />
          </div>
          {/* Keeps the focus in the search box while an option is pressed. */}
          <ul id={listId} role="listbox" aria-label="Stations" onMouseDown={(event) => event.preventDefault()} className="max-h-72 overflow-y-auto p-1.5">
            {shown.length === 0 ? (
              <li role="presentation" className="px-3 py-3 text-fg-muted">
                No station matches
              </li>
            ) : (
              shown.map((station, index) => {
                const selected = station.id === value;
                return (
                  <li
                    key={station.id}
                    id={optionId(station.id)}
                    role="option"
                    aria-selected={selected}
                    onClick={() => choose(station.id)}
                    onMouseEnter={() => setActive(index)}
                    className={`flex min-h-11 cursor-pointer items-center justify-between rounded-lg px-3 text-base sm:min-h-10 sm:text-sm ${
                      index === active ? "bg-surface-raised" : ""
                    } ${selected ? "font-medium text-white" : "text-fg"}`}
                  >
                    <span>{station.name}</span>
                    {selected ? (
                      <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="var(--color-model-ecmwf)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                        <path d="M3 8.5l3.2 3L13 4.5" />
                      </svg>
                    ) : null}
                  </li>
                );
              })
            )}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
