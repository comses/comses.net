import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import GitHubSyncOverview from "@/components/GitHubSyncOverview.vue";

createApp(GitHubSyncOverview).mount("#github-sync-overview");
