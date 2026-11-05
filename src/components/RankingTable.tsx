import { Card, CardSubtitle, CardTitle } from "@/components/Card";
import { ColumnGuide } from "@/components/ColumnGuide";
import { CountUpNumber } from "@/components/CountUp";
import { Fade } from "@/components/Fade";
import { ModelName } from "@/components/ModelName";
import type { RankedModel, Variable, Verdict } from "@/lib/api/types";
import { modelTint } from "@/lib/models";
import { formatNumber, formatPercent } from "@/lib/format";

/** `rain` is the precipitation verdict, or undefined while it is loading or failed: its columns then show a dash. */
type Props = { variable: Variable; verdict: Verdict; rain: Verdict | undefined };

export type Column = {
  key: string;
  header: string;
  hint: string;
  /** Which way is better: a lower number, a higher one, or one close to zero. */
  better: "lower" | "higher" | "zero";
  value: (model: RankedModel, rain: RankedModel | undefined) => number | null | undefined;
  format: (value: number) => string;
};

/** The columns depend on what is being judged: measured quantities get an error and a bias, rain gets its yes/no scores. */
function columns(variable: Variable): Column[] {
  if (variable.metric === "accuracy") {
    return [
      { key: "accuracy", header: "Accuracy", better: "higher", hint: "Share of wet or dry calls that were right.", value: (m) => m.accuracy, format: formatPercent },
      { key: "hit", header: "Rain caught", better: "higher", hint: "Share of rainy days the forecast called.", value: (m) => m.hit_rate, format: formatPercent },
      { key: "false", header: "False alarms", better: "lower", hint: "Share of rain calls made on days that stayed dry.", value: (m) => m.false_alarm_ratio, format: formatPercent },
      { key: "brier", header: "Brier", better: "lower", hint: "Score for rain chances, from 0 (perfect) to 1.", value: (m) => m.brier, format: (n) => formatNumber(n, 2) },
    ];
  }
  return [
    { key: "error", header: `Error (${variable.unit})`, better: "lower", hint: "Average gap between forecast and measurement.", value: (m) => m.mae, format: (n) => formatNumber(n) },
    { key: "bias", header: `Bias (${variable.unit})`, better: "zero", hint: "Whether the forecast runs high (+) or low (−) on average.", value: (m) => m.bias, format: formatSigned },
    { key: "rain", header: "Rain accuracy", better: "higher", hint: "Share of wet or dry calls that were right.", value: (_m, rain) => rain?.accuracy, format: formatPercent },
    { key: "brier", header: "Brier", better: "lower", hint: "Score for rain chances, from 0 (perfect) to 1.", value: (_m, rain) => rain?.brier, format: (n) => formatNumber(n, 2) },
  ];
}

function formatSigned(value: number): string {
  const text = formatNumber(Math.abs(value), 1);
  return value > 0.05 ? `+${text}` : value < -0.05 ? `−${text}` : text;
}

export function RankingTable({ variable, verdict, rain }: Props) {
  const cols = columns(variable);
  const best = verdict.ranking.find((model) => model.rank === 1) ?? verdict.ranking[0];
  const rainBy = new Map((rain?.ranking ?? []).map((model) => [model.model, model]));
  const first = verdict.lead_from;
  const last = verdict.lead_to;

  return (
    <Card as="section" delay={260} className="flex-[2_1_100%] lg:flex-[2_1_22rem]">
      <CardTitle>Model ranking</CardTitle>
      <CardSubtitle>
        <Fade id={`${first}-${last}|${verdict.station.name}`}>
          {first}–{last} day forecasts, {verdict.station.name}
        </Fade>
      </CardSubtitle>

      {verdict.ranking.length === 0 ? (
        <p className="mt-4 text-fg-muted">No scored forecasts in this window yet.</p>
      ) : (
        <>
          <div className="mt-4 hidden overflow-x-auto md:block">
            <table className="w-full border-collapse tabular-nums">
              <caption className="sr-only">Models ranked by {variable.metric === "accuracy" ? "accuracy" : "error"}</caption>
              <thead>
                <tr className="text-xs text-fg-muted">
                  <th scope="col" className="border-b border-border px-3 py-2 text-left font-medium">
                    Model
                  </th>
                  {cols.map((col) => (
                    <th key={col.key} scope="col" className="border-b border-border px-3 py-2 text-right font-medium">
                      <Fade id={col.header}>{col.header}</Fade>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {verdict.ranking.map((model) => {
                  const tint = model.rank === 1 ? modelTint(model.model) : undefined;
                  return (
                    <tr key={model.model} className="transition-colors hover:bg-surface-raised" style={tint ? { background: tint.background } : undefined}>
                      <th scope="row" className="whitespace-nowrap px-3 py-3 text-left font-medium" style={tint ? { boxShadow: tint.edge } : undefined}>
                        <span className="mr-2 font-mono text-fg-muted">{model.rank ?? "–"}</span>
                        <ModelName id={model.model} label={model.label} />
                        {model.rank === null ? <span className="ml-2 text-xs font-normal text-fg-muted">too few days</span> : null}
                      </th>
                      {cols.map((col) => (
                        <td key={col.key} className="px-3 py-3 text-right font-mono">
                          <CountUpNumber value={col.value(model, rainBy.get(model.model)) ?? null} format={col.format} />
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <ul className="mt-4 flex flex-col gap-2 md:hidden">
            {verdict.ranking.map((model) => (
              <li
                key={model.model}
                className={`rounded-[10px] p-3 ${model.rank === 1 ? "" : "bg-surface-raised"}`}
                style={model.rank === 1 ? { background: modelTint(model.model).background, boxShadow: modelTint(model.model).edge } : undefined}
              >
                <div className="font-medium">
                  <span className="mr-2 font-mono text-fg-muted">{model.rank ?? "–"}</span>
                  <ModelName id={model.model} label={model.label} />
                  {model.rank === null ? <span className="ml-2 text-xs font-normal text-fg-muted">too few days</span> : null}
                </div>
                <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                  {cols.map((col) => (
                    <div key={col.key} className="flex items-baseline justify-between gap-2">
                      <dt className="text-fg-muted">{col.header}</dt>
                      <dd className="font-mono"><CountUpNumber value={col.value(model, rainBy.get(model.model)) ?? null} format={col.format} /></dd>
                    </div>
                  ))}
                </dl>
              </li>
            ))}
          </ul>

          {best ? <ColumnGuide columns={cols} variable={variable} best={best} bestRain={rainBy.get(best.model)} /> : null}
        </>
      )}
    </Card>
  );
}
