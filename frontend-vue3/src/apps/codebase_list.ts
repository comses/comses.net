import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import CodebaseListSidebar from "@/components/CodebaseListSidebar.vue";
import SortBy from "@/components/ListSortBy.vue";

createApp(CodebaseListSidebar).mount("#sidebar");
createApp(SortBy, {
  sortOptions: [
    { value: "", label: "Relevance" },
    { value: "-first_published_at", label: "Publish date: newest" },
    { value: "first_published_at", label: "Publish date: oldest" },
    { value: "last_modified", label: "Last Modified" },
  ],
}).mount("#sortby");
