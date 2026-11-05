import { Card, CardSubtitle, CardTitle } from "@/components/Card";
import { ModelName } from "@/components/ModelName";
import { headlineValue } from "@/components/metric";
import type { RankedModel, Variable, Verdict } from "@/lib/api/types";
import { formatNumber, formatPercent } from "@/lib/format";

/** `rain` is the precipitation verdict, or undefined while it is loading or failed: its columns then show a dash. */
type Props = { variable: Variable; verdict: Verdict; rain: Verdict | undefined };

type Column = { key: string; header: string; cell: (model: RankedModel, rain: RankedModel | undefined) => string };

/** The columns depend on what is being judged: measured quantities get an error and a bias, rain gets its yes/no scores. */
function columns(variable: Variable): Column[] {
  if (variable.metric === "accuracy") {
    return [
      { key: "accuracy", header: "Accuracy", cell: (m) => formatPercent(m.accuracy) },
      { key: "hit", header: "Rain caught", cell: (m) => formatPercent(m.hit_rate) },
      { key: "false", header: "False alarms", cell: (m) => formatPercent(m.false_alarm_ratio) },
      { key: "brier", header: "Brier", cell: (m) => formatNumber(m.brier, 2) },
    ];
  }
  return [
    { key: "error", header: `Error (${variable.unit})`, cell: (m) => headlineValue(variable, m) },
    { key: "bias", header: `Bias (${variable.unit})`, cell: (m) => formatSigned(m.bias) },
    { key: "rain", header: "Rain accuracy", cell: (_m, rain) => formatPercent(rain?.accuracy) },
    { key: "brier", header: "Brier", cell: (_m, rain) => formatNumber(rain?.brier, 2) },
  ];
}

function formatSigned(value: number | null): string {
  if (value === null) return "–";
  const text = formatNumber(Math.abs(value), 1);
  return value > 0.05 ? `+${text}` : value < -0.05 ? `−${text}` : text;
}

export function RankingTable({ variable, verdict, rain }: Props) {
  const cols = columns(variable);
  const rainBy = new Map((rain?.ranking ?? []).map((model) => [model.model, model]));
  const first = verdict.lead_from;
  const last = verdict.lead_to;

  return (
    <Card as="section" delay={260} className="flex-[2_1_100%] lg:flex-[2_1_22rem]">
      <CardTitle>Model ranking</CardTitle>
      <CardSubtitle>
        {first}–{last} day forecasts, {verdict.station.name}
      </CardSubtitle>

      {verdict.ranking.length === 0 ? (
        <p className="mt-4 text-fg-muted">No scored forecasts in this window yet.</p>
      ) : (
        <>
          <div className="mt-4 hidden overflow-x-auto md:block lg:block">
            <table className="w-full border-collapse tabular-nums">
              <caption className="sr-only">Models ranked by {variable.metric === "accuracy" ? "accuracy" : "error"}</caption>
              <thead>
                <tr className="text-xs text-fg-muted">
                  <th scope="col" className="border-b border-border px-3 py-2 text-left font-medium">
                    Model
                  </th>
                  {cols.map((col) => (
                    <th key={col.key} scope="col" className="border-b border-border px-3 py-2 text-right font-medium">
                      {col.header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {verdict.ranking.map((model) => (
                  <tr key={model.model} className={`transition-colors hover:bg-surface-raised ${model.rank === 1 ? "bg-highlight" : ""}`}>
                    <th scope="row" className="whitespace-nowrap px-3 py-3 text-left font-medium">
                      <span className="mr-2 font-mono text-fg-muted">{model.rank ?? "–"}</span>
                      <ModelName id={model.model} label={model.label} />
                      {model.rank === null ? <span className="ml-2 text-xs font-normal text-fg-muted">too few days</span> : null}
                    </th>
                    {cols.map((col) => (
                      <td key={col.key} className="px-3 py-3 text-right font-mono">
                        {col.cell(model, rainBy.get(model.model))}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <ul className="mt-4 flex flex-col gap-2 md:hidden">
            {verdict.ranking.map((model) => (
              <li key={model.model} className={`rounded-[10px] p-3 ${model.rank === 1 ? "bg-highlight" : "bg-surface-raised"}`}>
                <div className="font-medium">
                  <span className="mr-2 font-mono text-fg-muted">{model.rank ?? "–"}</span>
                  <ModelName id={model.model} label={model.label} />
                  {model.rank === null ? <span className="ml-2 text-xs font-normal text-fg-muted">too few days</span> : null}
                </div>
                <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                  {cols.map((col) => (
                    <div key={col.key} className="flex items-baseline justify-between gap-2">
                      <dt className="text-fg-muted">{col.header}</dt>
                      <dd className="font-mono">{col.cell(model, rainBy.get(model.model))}</dd>
                    </div>
                  ))}
                </dl>
              </li>
            ))}
          </ul>
        </>
      )}
    </Card>
  );
}
