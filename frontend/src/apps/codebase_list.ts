import "vite/modulepreload-polyfill"; // Ensure that this is needed based on your project setup

import { createApp } from "vue";
import CodebaseListSidebar from "@/components/CodebaseListSidebar.vue";
import SortBy from "@/components/ListSortBy.vue";
import { extractDataParams } from "@/util";

const props = extractDataParams("sidebar", ["languageFacets"]);
createApp(CodebaseListSidebar, props).mount("#sidebar");

// Function to check if 'query' exists and is not empty
function hasQueryParam(param: string) {
  const params = new URLSearchParams(window.location.search);
  const value = params.get(param);
  return value !== null && value.trim() !== "";
}

const relevanceOption = hasQueryParam("query") ? [{ value: "relevance", label: "Relevance" }] : [];

const sortOptions = [
  ...relevanceOption,
  { value: "-first_published_at", label: "Publish date: newest" },
  { value: "first_published_at", label: "Publish date: oldest" },
  { value: "-last_modified", label: "Recently Modified" },
];

createApp(SortBy, { sortOptions }).mount("#sortby");
