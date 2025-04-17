import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import HomepageFeed from "@/components/HomepageFeed.vue";
import { extractDataParams } from "@/util";

const feeds = ["forum", "events", "jobs"];

for (const feed of feeds) {
  const props = extractDataParams(`${feed}-feed`, ["title", "link", "feed"]);
  createApp(HomepageFeed, props).mount(`#${feed}-feed`);
}
