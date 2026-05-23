import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import GitHubIntegrationOverview from "@/components/GitHubIntegrationOverview.vue";

createApp(GitHubIntegrationOverview).mount("#github-overview");
