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
