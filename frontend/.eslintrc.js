module.exports = {
  parser: "vue-eslint-parser",
  parserOptions: {
    parser: "@typescript-eslint/parser",
  },
  extends: ["eslint:recommended", "plugin:vue/essential", "@vue/eslint-config-typescript"],
  rules: {
    "no-useless-constructor": "off",
    "no-empty-function": "off",
    "import/prefer-default-export": "off",
  },
  ignorePatterns: ["node_modules/*", "public/*", "dist/*"],
  settings: {
    "import/resolver": {
      typescript: {
        alwaysTryTypes: true,
      },
    },
  },
};
