import "vite/modulepreload-polyfill";

import { createApp } from "vue";
import FeedPosts from "@/components/FeedPosts.vue";
import FeedCodebases from "@/components/FeedCodebases.vue";
import FeedThumbnailGrid from "@/components/FeedThumbnailGrid.vue";
import FeedForumCategories from "@/components/FeedForumCategories.vue";
import { extractDataParams } from "@/util";

const propsParams = ["feedUrl", "limit", "datePrefix", "authorPrefix"];

const feedConfigs = [
  {
    elementId: "reviewed-models-feed",
    component: FeedCodebases,
    dataParams: propsParams,
  },
  {
    elementId: "events-feed",
    component: FeedPosts,
    dataParams: propsParams,
  },
  {
    elementId: "jobs-feed",
    component: FeedPosts,
    dataParams: propsParams,
  },
  {
    elementId: "forum-categories-feed",
    component: FeedForumCategories,
    dataParams: propsParams,
  },
  {
    elementId: "youtube-feed",
    component: FeedThumbnailGrid,
    dataParams: propsParams,
  },
];

feedConfigs.forEach(({ elementId, component, dataParams }) => {
  const element = document.getElementById(elementId);

  if (element) {
    try {
      const props = extractDataParams(elementId, dataParams);
      createApp(component, props).mount(`#${elementId}`);
    } catch (error) {
      console.warn(`Failed to initialize feed component for ${elementId}:`, error);
    }
  }
});
