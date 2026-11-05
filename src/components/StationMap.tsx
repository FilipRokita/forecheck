"use client";

import { useState } from "react";
import { ModelName } from "@/components/ModelName";
import type { Comparison } from "@/lib/api/types";
import { modelColor } from "@/lib/models";
import { MAP_HEIGHT, MAP_WIDTH, POLAND_OUTLINE, project } from "@/lib/poland";

type Props = {
  rows: Comparison["rows"];
  selectedStation: string;
  onSelect: (stationId: string) => void;
};

/**
 * The stations on a map of Poland, each dot in the colour of its best model. It is a second way in to what the table
 * beside it already says, so it is hidden from assistive technology and the table stays the accessible version.
 */
export function StationMap({ rows, selectedStation, onSelect }: Props) {
  const [hovered, setHovered] = useState<string | null>(null);
  const labelled = rows.find((row) => row.station.id === (hovered ?? selectedStation));
  const models = new Map(rows.flatMap((row) => (row.best_model && row.best_model_label ? [[row.best_model, row.best_model_label] as const] : [])));

  return (
    <div>
      <svg viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`} aria-hidden="true" className="mx-auto w-full max-w-md">
        <path d={POLAND_OUTLINE} className="fill-surface-raised stroke-border-strong" strokeWidth="1.5" strokeLinejoin="round" />
        {rows.map((row, index) => {
          const { x, y } = project(row.station.latitude, row.station.longitude);
          const selected = row.station.id === selectedStation;
          const color = row.best_model ? modelColor(row.best_model) : "var(--color-fg-muted)";
          return (
            <g
              key={row.station.id}
              data-station={row.station.id}
              transform={`translate(${x} ${y})`}
              className="animate-fade cursor-pointer"
              style={{ animationDelay: `${300 + index * 40}ms` }}
              onMouseEnter={() => setHovered(row.station.id)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => onSelect(row.station.id)}
            >
              <circle r="16" fill="transparent" />
              {selected ? <circle r="9" fill="none" strokeWidth="1.5" className="animate-ping-soft [transform-box:fill-box] origin-center" style={{ stroke: color }} /> : null}
              <circle
                r={selected ? 8.5 : 6.5}
                strokeWidth="2"
                className="stroke-bg transition-transform duration-150 [transform-box:fill-box] origin-center hover:scale-125"
                style={{ fill: color }}
              />
            </g>
          );
        })}
        {labelled
          ? (() => {
              const { x, y } = project(labelled.station.latitude, labelled.station.longitude);
              return (
                <text x={x} y={y - 14} textAnchor="middle" className="pointer-events-none fill-fg text-[13px] font-medium" stroke="var(--color-bg)" strokeWidth="4" paintOrder="stroke">
                  {labelled.station.name}
                </text>
              );
            })()
          : null}
      </svg>
      <ul className="mt-3 flex flex-wrap justify-center gap-x-4 gap-y-1 text-fg-soft" aria-label="Map legend">
        {[...models].map(([id, label]) => (
          <li key={id}>
            <ModelName id={id} label={label} />
          </li>
        ))}
      </ul>
    </div>
  );
}
