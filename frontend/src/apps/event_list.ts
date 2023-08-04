import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import EventListSidebar from "@/components/EventListSidebar.vue";
import SortBy from "@/components/ListSortBy.vue";

createApp(EventListSidebar).mount("#sidebar");
createApp(SortBy, {
  sortOptions: [
    { label: "Relevance", value: "" },
    { label: "Date posted: newest", value: "-date_created" },
    { label: "Date posted: oldest", value: "date_created" },
    { label: "Start date", value: "start_date" },
    { label: "Submission deadline", value: "submission_deadline" },
    { label: "Early reg. deadline", value: "early_registration_deadline" },
    { label: "Recently modified", value: "-last_modified" },
  ],
}).mount("#sortby");
