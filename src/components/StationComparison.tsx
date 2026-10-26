import { Card, CardSubtitle, CardTitle } from "@/components/Card";
import { ModelName } from "@/components/ModelName";
import { headline } from "@/components/metric";
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
    <Card as="section">
      <CardTitle>Station comparison</CardTitle>
      <CardSubtitle>
        {variable.label}, {comparison.lead_days}-day forecasts, last {period.label}. Choose a station to open it.
      </CardSubtitle>

      <div className="mt-4 overflow-x-auto">
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
                <tr key={row.station.id} className={`border-b border-grid last:border-0 ${selected ? "bg-highlight" : ""}`}>
                  <th scope="row" className="p-0 text-left font-normal">
                    <button
                      type="button"
                      aria-current={selected ? "true" : undefined}
                      onClick={() => onSelect(row.station.id)}
                      className="min-h-12 w-full px-3 text-left hover:text-white focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-model-ecmwf"
                    >
                      {row.station.name}
                    </button>
                  </th>
                  <td className="px-3 py-3">
                    {row.best_model && row.best_model_label ? (
                      <ModelName id={row.best_model} label={row.best_model_label} />
                    ) : (
                      <span className="text-fg-muted">Too few days</span>
                    )}
                  </td>
                  <td className="px-3 py-3 text-right font-mono">{row.figures ? headline(variable, row.figures) : "–"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
