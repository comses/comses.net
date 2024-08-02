import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import CodebaseListSidebar from "@/components/CodebaseListSidebar.vue";
import SortBy from "@/components/ListSortBy.vue";

let programmingLanguages = {};

if (window.language_facets !== undefined) {
  try {
    programmingLanguages = JSON.parse(window.language_facets);
  } catch (error) {
    console.debug("Error parsing language_facets:", error);
  }
}

createApp(CodebaseListSidebar, { programmingLanguages: programmingLanguages }).mount("#sidebar");
createApp(SortBy, {
  sortOptions: [
    { value: "", label: "Relevance" },
    { value: "-first_published_at", label: "Publish date: newest" },
    { value: "first_published_at", label: "Publish date: oldest" },
    { value: "-last_modified", label: "Recently Modified" },
  ],
}).mount("#sortby");
