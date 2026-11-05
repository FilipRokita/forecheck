"use client";

import { useState } from "react";
import { ModelName } from "@/components/ModelName";
import type { Comparison } from "@/lib/api/types";
import { modelColor } from "@/lib/models";
import { MAP_HEIGHT, MAP_WIDTH, POLAND_OUTLINE, project } from "@/lib/poland";

type Props = {
  rows: Comparison["rows"];
  selectedStation: string;
};

/**
 * The stations on a map of Poland, each dot in the colour of its best model, with the name of the station under the pointer.
 * It is only to look at. It says what the table beside it already says, so it is hidden from assistive technology and the
 * table stays the accessible version.
 */
export function StationMap({ rows, selectedStation }: Props) {
  const [hovered, setHovered] = useState<string | null>(null);
  // The open station always keeps its name, and the one under the pointer is named as well. Every name stays in the picture and fades in or out, the hovered one drawn last so it is on top.
  const shown = (id: string) => id === selectedStation || id === hovered;
  const named = [...rows].sort((a, b) => Number(a.station.id === hovered) - Number(b.station.id === hovered));
  const models = new Map(rows.flatMap((row) => (row.best_model && row.best_model_label ? [[row.best_model, row.best_model_label] as const] : [])));

  return (
    <div>
      <svg viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`} aria-hidden="true" className="mx-auto w-full max-w-xl">
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
              className="animate-fade"
              style={{ animationDelay: `${300 + index * 40}ms` }}
              onMouseEnter={() => setHovered(row.station.id)}
              onMouseLeave={() => setHovered(null)}
            >
              <circle r="16" fill="transparent" />
              {selected ? <circle r="9" fill="none" strokeWidth="1.5" className="animate-ping-soft [transform-box:fill-box] origin-center" style={{ stroke: color }} /> : null}
              <circle
                r={selected ? 8.5 : 6.5}
                strokeWidth="2"
                className="stroke-bg transition-[transform,fill,r] duration-500 [transform-box:fill-box] origin-center"
                style={{ fill: color, transform: hovered === row.station.id ? "scale(1.25)" : "scale(1)" }}
              />
            </g>
          );
        })}
        {named.map((row) => {
          const { x, y } = project(row.station.latitude, row.station.longitude);
          return (
            <text
              key={row.station.id}
              x={x}
              y={y - 14}
              textAnchor="middle"
              className="pointer-events-none fill-fg text-[13px] font-medium transition-opacity duration-300"
              style={{ opacity: shown(row.station.id) ? 1 : 0 }}
              stroke="var(--color-bg)"
              strokeWidth="4"
              paintOrder="stroke"
            >
              {row.station.name}
            </text>
          );
        })}
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
