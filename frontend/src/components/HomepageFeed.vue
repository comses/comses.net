<template>
  <div class="row">
    <div class="col-9">
      <h3>{{ props.title }}</h3>
    </div>
    <div class="col-3 text-end">
      <small><a class="text-end" :href="props.link">View All</a></small>
    </div>
  </div>
  <div v-for="item in items" :key="item.title" class="activity">
    <h4>
      <a :href="item.link">{{ item.title }}</a>
    </h4>
    <small class="text-muted">
      <span v-if="item.summary">{{ item.summary }}<br /></span>
      <span v-if="item.author">Posted by {{ item.author }}</span>
      <span v-if="item.author && item.date"> - </span>
      <span v-if="item.date">{{
        item.date.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })
      }}</span>
    </small>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useHomepageFeedAPI } from "@/composables/api";
import type { HomepageFeedItem } from "@/types";

const items = ref<HomepageFeedItem[]>([]);

const homepageFeedAPI = useHomepageFeedAPI();

const props = defineProps<{
  title: string;
  link: string;
  feed: "Events" | "ForumPosts" | "Jobs";
}>();

onMounted(async () => {
  const response = await homepageFeedAPI[`get${props.feed}`]();
  // TODO error handling
  if (response.data.items) {
    items.value = response.data.items;
    console.log(items.value);
  }
});
</script>
