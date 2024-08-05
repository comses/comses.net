const { defineConfig } = require("cypress");

module.exports = defineConfig({
  e2e: {
    baseUrl: "http://localhost:8000",
    specPattern: ["cypress/tests/**/*.spec.ts"],
    supportFile: false,
    screenshotOnRunFailure: false,
    video: true,
  }
});
