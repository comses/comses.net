import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import JobListSidebar from "@/components/JobListSidebar.vue";
import SortBy from "@/components/ListSortBy.vue";

createApp(JobListSidebar).mount("#sidebar");
createApp(SortBy, {
  sortOptions: [
    { label: "Relevance", value: "" },
    { label: "Application deadline", value: "application_deadline" },
    { label: "Date posted", value: "date_created" },
    { label: "Recently modified ", value: "last_modified" },
  ],
}).mount("#sortby");
