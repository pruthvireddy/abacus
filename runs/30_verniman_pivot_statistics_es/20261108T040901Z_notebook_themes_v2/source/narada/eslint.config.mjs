import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";
import js from "@eslint/js";
import globals from "globals";

export default defineConfig([
  ...nextVitals,
  ...nextTypescript,
  {
    name: "narada/node-operations",
    files: ["scripts/**/*.mjs", "tests/**/*.mjs"],
    languageOptions: { globals: globals.node },
    rules: {
      ...js.configs.recommended.rules,
      "no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    },
  },
  globalIgnores([
    ".next/**", "out/**", "node_modules/**", "next-env.d.ts",
    ".release-artifacts/**", "releases/**", "archives/**", "provenance/**",
  ]),
]);
