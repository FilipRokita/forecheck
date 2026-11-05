/** The colour of each model. The same colour means the same model everywhere on the page, and it is always
 * backed by the model's name and its position, never by colour alone. */
const COLORS: Record<string, string> = {
  icon: "var(--color-model-icon)",
  ecmwf: "var(--color-model-ecmwf)",
  gfs: "var(--color-model-gfs)",
};

export function modelColor(modelId: string): string {
  return COLORS[modelId] ?? "var(--color-fg-muted)";
}

/** The highlight of a row that belongs to a model: a faint wash of the model's colour and a bar of it on the left edge. */
export function modelTint(modelId: string): { background: string; edge: string } {
  const color = modelColor(modelId);
  return { background: `color-mix(in srgb, ${color} 10%, var(--color-surface))`, edge: `inset 3px 0 0 ${color}` };
}
