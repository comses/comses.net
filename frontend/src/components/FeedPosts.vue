<template>
  <!-- loading feed-placeholder -->
  <template v-if="loading">
    <div v-for="n in props.limit" :key="`feed-placeholder-${n}`" class="p-3 mb-3">
      <div class="mb-2">
        <span class="feed-placeholder col-7 feed-placeholder-lg"></span>
      </div>
      <small class="text-muted">
        <span class="feed-placeholder col-4"></span>
        <span class="feed-placeholder col-3 ms-2"></span>
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
