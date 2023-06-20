import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import CodebaseListSidebar from "@/components/CodebaseListSidebar.vue";
import SortBy from "@/components/ListSortBy.vue";

createApp(CodebaseListSidebar).mount("#sidebar");
createApp(SortBy, {
  sortOptions: [
    { value: "", label: "Relevance" },
    { value: "-firstPublishedAt", label: "Publish date: newest" },
    { value: "firstPublishedAt", label: "Publish date: oldest" },
    { value: "lastModified", label: "Recently Modified" },
  ],
}).mount("#sortby");
