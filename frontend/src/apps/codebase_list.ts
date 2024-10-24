import "vite/modulepreload-polyfill"; // Ensure that this is needed based on your project setup

import { isEmpty } from "lodash";
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
  return !isEmpty(value);
}

const relevanceOption = hasQueryParam("query") ? [{ value: "relevance", label: "Relevance" }] : [];

const sortOptions = [
  ...relevanceOption,
  { value: "-first_published_at", label: "Most recently published" },
  { value: "first_published_at", label: "Earliest published" },
  { value: "-last_modified", label: "Recently modified" },
];

createApp(SortBy, { sortOptions }).mount("#sortby");
