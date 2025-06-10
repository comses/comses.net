<template>
  <!-- loading feed-placeholder -->
  <template v-if="loading">
    <div class="d-flex flex-row gap-2">
      <div
        v-for="n in props.limit"
        :key="`feed-placeholder-${n}`"
        class="badge border text-secondary d-flex align-items-center gap-1"
      >
        <span class="category-color-square feed-placeholder"></span>
        <span class="feed-placeholder" style="width: 60px; height: 14px"></span>
      </div>
    </div>
  </template>

  <!-- actual content -->
  <template v-else>
    <div class="d-flex flex-row gap-2 flex-wrap">
      <a
        v-for="item in items"
        :key="item.title"
        class="badge border text-secondary d-flex align-items-center gap-1"
        :href="item.link"
      >
        <span class="category-color-square" :style="{ backgroundColor: item.color }"></span>
        {{ item.title }}
      </a>
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

<style scoped>
.category-color-square {
  width: 10px;
  height: 10px;
  flex-shrink: 0;
}
</style>
