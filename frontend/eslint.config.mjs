import js from "@eslint/js";
import pluginVue from "eslint-plugin-vue";
import skipFormattingConfig from "@vue/eslint-config-prettier/skip-formatting";
import { withVueTs, vueTsConfigs } from "@vue/eslint-config-typescript";

export default withVueTs(
  {
    rootDir: import.meta.dirname,
  },
  {
    ignores: [
      "node_modules/",
      "dist/",
      "dist-ssr/",
      "coverage/",
      "logs/",
      "cypress/videos/",
      "cypress/screenshots/",
    ],
  },
  js.configs.recommended,
  pluginVue.configs["flat/essential"],
  vueTsConfigs.recommended,
  skipFormattingConfig,
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-require-imports": "off",
      "@typescript-eslint/no-unused-vars": ["warn", { varsIgnorePattern: "props" }],
    },
  },
);
