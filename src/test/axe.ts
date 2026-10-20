import axe from "axe-core";

/** Runs axe-core on the rendered page and returns the violations, as readable text. Contrast needs a real
 * browser engine, so that rule is off here; the colours are checked against the token table by hand. */
export async function accessibilityViolations(container: Element): Promise<string[]> {
  const results = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
  return results.violations.map((violation) => `${violation.id}: ${violation.help} (${violation.nodes.length} elements)`);
}
