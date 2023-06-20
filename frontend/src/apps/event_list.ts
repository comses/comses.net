import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import EventListSidebar from "@/components/EventListSidebar.vue";
import SortBy from "@/components/ListSortBy.vue";

createApp(EventListSidebar).mount("#sidebar");
createApp(SortBy, {
  sortOptions: [
    { label: "Relevance", value: "" },
    { label: "Date posted: newest", value: "-dateCreated" },
    { label: "Date posted: oldest", value: "dateCreated" },
    { label: "Start date", value: "startDate" },
    { label: "Submission deadline", value: "submissionDeadline" },
    { label: "Early reg. deadline", value: "earlyRegistrationDeadline" },
    { label: "Recently modified", value: "lastModified" },
  ],
}).mount("#sortby");
