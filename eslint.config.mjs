import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import boundaries from "eslint-plugin-boundaries";

/**
 * The layers of the view and who may import whom. A violation fails lint, and lint runs in CI.
 * The view has no domain logic: it formats and shows what the API returns.
 */
const layers = {
  api: { pattern: "src/lib/api/**", allow: ["api"] },
  lib: { pattern: "src/lib/**", allow: ["api", "lib"] },
  components: { pattern: "src/components/**", allow: ["api", "lib", "components"] },
  app: { pattern: "src/app/**", allow: ["api", "lib", "components", "app"] },
};

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([".next/**", "out/**", "build/**", "coverage/**", "next-env.d.ts", "src/lib/api/schema.ts", "public/**", "plans/**", "dev-only/**", ".venv/**", "backend/**"]),
  { rules: { "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }] } },
  {
    files: ["src/**/*.{ts,tsx}"],
    ignores: ["src/**/*.test.{ts,tsx}", "src/test/**"],
    plugins: { boundaries },
    settings: {
      "import/resolver": { typescript: { alwaysTryTypes: true, project: "./tsconfig.json" } },
      "boundaries/elements": Object.entries(layers).map(([type, { pattern }]) => ({ type, pattern })),
    },
    rules: {
      "boundaries/dependencies": [
        "error",
        {
          default: "disallow",
          policies: Object.entries(layers).map(([type, { allow }]) => ({ from: { element: { type } }, allow: { to: { element: { type: allow } } } })),
        },
      ],
    },
  },
]);
