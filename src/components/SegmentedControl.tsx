"use client";

import { useLayoutEffect, useRef, useState } from "react";

type Option = { id: string; label: string };

type Props = {
  label: string;
  options: readonly Option[];
  value: string;
  onChange: (id: string) => void;
  /** Scrolls sideways instead of wrapping, for a row that is too long for a phone. */
  scroll?: boolean;
};

type Box = { x: number; y: number; width: number; height: number };

export function SegmentedControl({ label, options, value, onChange, scroll = false }: Props) {
  const group = useRef<HTMLDivElement>(null);
  // Where the selected button is. The highlight is one element that slides there, instead of a style that jumps between buttons.
  const [box, setBox] = useState<Box | null>(null);

  useLayoutEffect(() => {
    const element = group.current;
    if (!element) return;
    const place = () => {
      const selected = element.querySelector<HTMLElement>("[aria-pressed='true']");
      if (selected) setBox({ x: selected.offsetLeft, y: selected.offsetTop, width: selected.offsetWidth, height: selected.offsetHeight });
    };
    place();
    // The buttons change size with the window and with the font loading.
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(place);
    observer?.observe(element);
    return () => observer?.disconnect();
  }, [value, options]);

  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-xs text-fg-muted max-sm:sr-only" id={`${label}-label`}>
        {label}
      </span>
      <div
        ref={group}
        role="group"
        aria-labelledby={`${label}-label`}
        className={`relative flex gap-1 rounded-xl border border-border bg-surface p-1 ${scroll ? "overflow-x-auto" : ""}`}
      >
        {box ? (
          <span
            aria-hidden="true"
            className="pointer-events-none absolute left-0 top-0 rounded-lg border border-border-strong bg-surface-raised shadow-md shadow-black/40 transition-[transform,width,height] duration-300 ease-out-soft"
            style={{ width: box.width, height: box.height, transform: `translate(${box.x}px, ${box.y}px)` }}
          />
        ) : null}
        {options.map((option) => {
          const selected = option.id === value;
          return (
            <button
              key={option.id}
              type="button"
              aria-pressed={selected}
              onClick={() => onChange(option.id)}
              className={`relative min-h-11 flex-none rounded-lg border border-transparent px-4 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-model-ecmwf sm:min-h-9 sm:px-3.5 ${
                selected ? "font-medium text-white" : "text-fg-muted hover:bg-surface-raised/60 hover:text-fg"
              } ${scroll ? "" : "flex-1 sm:flex-none"}`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
