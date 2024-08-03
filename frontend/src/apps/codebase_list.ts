import "vite/modulepreload-polyfill"; // Ensure that this is needed based on your project setup

import { createApp } from "vue";
import CodebaseListSidebar from "@/components/CodebaseListSidebar.vue";
import SortBy from "@/components/ListSortBy.vue";

// Extend the Window interface to include language_facets
declare global {
  interface Window {
    language_facets: string | undefined;
  }
}

// Define types for language facets
interface LanguageFacets {
  [key: string]: number;
}

export interface LanguageFacet {
  name: string;
  value: number;
}

// Parse language facets from the global window object
let languageFacets: LanguageFacet[] = [];

if (window.language_facets !== undefined) {
  try {
    const parsedLanguageFacets: LanguageFacets = JSON.parse(window.language_facets);
    languageFacets = Object.entries(parsedLanguageFacets).map(([name, value]) => ({
      name,
      value,
    }));
  } catch (error) {
    console.debug("Error parsing language_facets:", error);
  }
}

// Initialize the Vue app with the parsed data
createApp(CodebaseListSidebar, { languageFacets }).mount("#sidebar");

createApp(SortBy, {
  sortOptions: [
    { value: "", label: "Relevance" },
    { value: "-first_published_at", label: "Publish date: newest" },
    { value: "first_published_at", label: "Publish date: oldest" },
    { value: "-last_modified", label: "Recently Modified" },
  ],
}).mount("#sortby");
