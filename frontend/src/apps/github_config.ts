import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import { extractDataParams } from "@/util";
import GitHubIntegrationConfiguration from "@/components/GitHubIntegrationConfiguration.vue";

const props = extractDataParams("github-config", [
  "codebaseIdentifier",
  "githubOrgName",
  "defaultRepoName",
  "isCodebaseLive",
  "enableNewSyncs",
]);
createApp(GitHubIntegrationConfiguration, props).mount("#github-config");
