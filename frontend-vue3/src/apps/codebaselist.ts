import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import CodebaseSearch from "@/components/CodebaseSearch.vue";

createApp(CodebaseSearch).mount("#search");
