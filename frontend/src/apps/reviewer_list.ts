import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import ReviewersPage from "@/components/ReviewersPage.vue";
// import { extractDataParams } from "@/util";

createApp(ReviewersPage).mount("#reviewer-list");
