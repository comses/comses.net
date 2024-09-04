import "vite/modulepreload-polyfill"; // Ensure that this is needed based on your project setup

import { createApp } from "vue";
import CodebaseListSidebar from "@/components/CodebaseListSidebar.vue";
import SortBy from "@/components/ListSortBy.vue";
import { extractDataParams } from "@/util";

const props = extractDataParams("sidebar", ["languageFacets"]);
createApp(CodebaseListSidebar, props).mount("#sidebar");

createApp(SortBy, {
  sortOptions: [
    { value: "relevance", label: "Relevance" },
    { value: "-first_published_at", label: "Publish date: newest" },
    { value: "first_published_at", label: "Publish date: oldest" },
    { value: "-last_modified", label: "Recently Modified" },
  ],
}).mount("#sortby");
