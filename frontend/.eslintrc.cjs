/* eslint-env node */
require('@rushstack/eslint-patch/modern-module-resolution')

module.exports = {
  root: true,
  'extends': [
    'plugin:vue/vue3-essential',
    'eslint:recommended',
    '@vue/eslint-config-typescript',
    '@vue/eslint-config-prettier/skip-formatting'
  ],
  rules: {
    '@typescript-eslint/no-unused-vars': [
      'warn',
      { 'varsIgnorePattern': "props" }
    ],
  },
  parserOptions: {
    ecmaVersion: 'latest'
  }
}
