import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import JobListSidebar from "@/components/JobListSidebar.vue";
import SortBy from "@/components/ListSortBy.vue";

createApp(JobListSidebar).mount("#sidebar");
createApp(SortBy, {
  sortOptions: [
    { label: "Relevance", value: "" },
    { label: "Date posted: newest", value: "-date_created" },
    { label: "Date posted: oldest", value: "date_created" },
    { label: "Deadline: furthest", value: "-application_deadline" },
    { label: "Deadline: nearest", value: "application_deadline" },
    { label: "Recently modified ", value: "last_modified" },
  ],
}).mount("#sortby");
