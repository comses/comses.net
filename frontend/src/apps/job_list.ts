import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import JobListSidebar from "@/components/JobListSidebar.vue";
import SortBy from "@/components/ListSortBy.vue";

createApp(JobListSidebar).mount("#sidebar");
createApp(SortBy, {
  sortOptions: [
    { label: "Relevance", value: "" },
    { label: "Date posted: newest", value: "-dateCreated" },
    { label: "Date posted: oldest", value: "dateCreated" },
    { label: "Deadline: furthest", value: "-applicationDeadline" },
    { label: "Deadline: nearest", value: "applicationDeadline" },
    { label: "Recently modified ", value: "lastModified" },
  ],
}).mount("#sortby");
