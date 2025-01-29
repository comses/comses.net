import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import { extractDataParams } from "@/util";
import GitHubSyncConfiguration from "@/components/GitHubSyncConfiguration.vue";

const props = extractDataParams("github-sync", ["codebaseIdentifier", "githubOrgName"]);
createApp(GitHubSyncConfiguration, props).mount("#github-sync");
