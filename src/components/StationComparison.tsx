import { Card, CardSubtitle, CardTitle } from "@/components/Card";
import { CountUpNumber } from "@/components/CountUp";
import { Fade } from "@/components/Fade";
import { ModelName } from "@/components/ModelName";
import { StationMap } from "@/components/StationMap";
import { headlineFormat, headlineNumber } from "@/components/metric";
import type { Comparison, Period, Variable } from "@/lib/api/types";

type Props = {
  comparison: Comparison;
  variable: Variable;
  period: Period;
  selectedStation: string;
  onSelect: (stationId: string) => void;
};

export function StationComparison({ comparison, variable, period, selectedStation, onSelect }: Props) {
  const valueHeader = variable.metric === "accuracy" ? "Accuracy" : `Error (${variable.unit})`;
  return (
    <Card as="section" delay={320}>
      <CardTitle>Station comparison</CardTitle>
      <CardSubtitle>
        <Fade id={`${variable.id}|${period.id}`}>
          {variable.label}, {comparison.lead_days}-day forecasts, last {period.label}. Choose a station to open it.
        </Fade>
      </CardSubtitle>

      <div className="mt-4 grid gap-6 lg:grid-cols-[minmax(0,32rem)_minmax(0,1fr)] lg:items-start">
        <div className="lg:sticky lg:top-24">
          <StationMap rows={comparison.rows} selectedStation={selectedStation} onSelect={onSelect} />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse tabular-nums">
            <caption className="sr-only">Best model and its {valueHeader.toLowerCase()} at every station</caption>
            <thead>
              <tr className="text-xs text-fg-muted">
                <th scope="col" className="border-b border-border px-3 py-2 text-left font-medium">
                  Station
                </th>
                <th scope="col" className="border-b border-border px-3 py-2 text-left font-medium">
                  Best model
                </th>
                <th scope="col" className="border-b border-border px-3 py-2 text-right font-medium">
                  {valueHeader}
                </th>
              </tr>
            </thead>
            <tbody>
              {comparison.rows.map((row) => {
                const selected = row.station.id === selectedStation;
                return (
                  <tr key={row.station.id} className={`border-b border-grid last:border-0 ${selected ? "bg-highlight" : "hover:bg-surface-raised"} transition-colors`}>
                    <th scope="row" className="p-0 text-left font-normal">
                      <button
                        type="button"
                        aria-current={selected ? "true" : undefined}
                        onClick={() => onSelect(row.station.id)}
                        className="min-h-12 w-full px-3 lg:min-h-10 text-left hover:text-white focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-model-ecmwf"
                      >
                        {row.station.name}
                      </button>
                    </th>
                    <td className="px-3 py-3 lg:py-2">
                      {row.best_model && row.best_model_label ? (
                        <ModelName id={row.best_model} label={row.best_model_label} />
                      ) : (
                        <span className="text-fg-muted">Too few days</span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-right font-mono lg:py-2">{row.figures ? <CountUpNumber value={headlineNumber(variable, row.figures)} format={headlineFormat(variable)} /> : "–"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </Card>
  );
}
