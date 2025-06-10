<template>
  <!-- loading feed-placeholder -->
  <template v-if="loading">
    <div
      v-for="n in props.limit"
      :key="`feed-placeholder-${n}`"
      class="feed-item p-3 mb-3 position-relative"
    >
      <div class="mb-2">
        <span
          class="placeholder placeholder-glow feed-placeholder feed-title clamp-2"
          style="width: 80%; height: 1.2em; display: block"
        ></span>
      </div>
      <small class="text-muted">
        <span
          class="placeholder placeholder-glow feed-placeholder"
          style="width: 4rem; height: 0.75em"
        ></span>
        <span
          class="placeholder placeholder-glow feed-placeholder ms-2"
          style="width: 6rem; height: 0.75em"
        ></span>
      </small>
    </div>
  </template>

  <!-- actual content -->
  <template v-else>
    <div v-for="item in items" :key="item.title" class="feed-item p-3 mb-3 position-relative">
      <div class="mb-2">
        <a :href="item.link" class="feed-title clamp-2">{{ item.title }}</a>
      </div>
      <small class="text-muted">
        <span v-if="item.author && props.authorPrefix">
          {{ props.authorPrefix }} {{ item.author }}
        </span>
        <span v-if="item.date && props.datePrefix">
          {{ props.datePrefix }}
          <b>
            {{
              item.date.toLocaleDateString("en-US", {
                year: "numeric",
                month: "short",
                day: "numeric",
                timeZone: "UTC",
              })
            }}
          </b>
        </span>
        <span v-else-if="!item.date && props.datePrefix" class="invisible">
          {{ props.datePrefix }}
        </span>
      </small>
    </div>
  </template>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useFeedAPI } from "@/composables/api";
import type { FeedItem, FeedProps } from "@/types";

const items = ref<FeedItem[]>([]);
const loading = ref(true);

const props = withDefaults(defineProps<FeedProps>(), {});

const { getFeed } = useFeedAPI();

onMounted(async () => {
  try {
    const response = await getFeed(props.feedUrl, props.limit);

    if (response.data.items) {
      items.value = response.data.items;
    }
  } catch (error) {
    console.error(`Failed to fetch feed data from ${props.feedUrl}:`, error);
  } finally {
    loading.value = false;
  }
});
</script>
