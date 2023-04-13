import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import CodebaseListSidebar from "@/components/CodebaseListSidebar.vue";

createApp(CodebaseListSidebar).mount("#search");
