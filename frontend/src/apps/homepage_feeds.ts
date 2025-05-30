import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import FeedBlock from "@/components/FeedBlock.vue";
import { extractDataParams } from "@/util";

const feeds = ["forum", "events", "jobs"];

for (const feed of feeds) {
  const props = extractDataParams(`${feed}-feed`, ["title", "link", "feed"]);
  createApp(FeedBlock, props).mount(`#${feed}-feed`);
}
