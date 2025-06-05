<template>
  <!-- loading feed-placeholder -->
  <template v-if="loading">
    <div
      v-for="n in props.limit"
      :key="`feed-placeholder-${n}`"
      class="activity border rounded p-3 mb-3"
    >
      <div class="d-flex">
        <div class="flex-shrink-0 me-3">
          <div class="feed-placeholder bg-gray rounded" style="width: 100px; height: 100px"></div>
        </div>
        <div class="flex-grow-1 d-flex flex-column">
          <h5 class="mb-2">
            <span class="feed-placeholder col-8 feed-placeholder-lg"></span>
          </h5>
          <div class="d-flex align-items-start justify-content-between mt-auto">
            <small class="text-muted">
              <span class="feed-placeholder col-6"></span>
              <br />
              <span class="feed-placeholder col-4"></span>
            </small>
          </div>
        </div>
      </div>
    </div>
  </template>

  <!-- actual content -->
  <template v-else>
    <div
      v-for="item in items"
      :key="item.title"
      class="activity border rounded mb-3 d-flex overflow-hidden"
    >
      <div class="flex-shrink-0" style="width: 8rem">
        <a v-if="item.thumbnail" class="d-block h-100" :href="item.link">
          <img
            :src="item.thumbnail"
            alt="Model image"
            class="img-fluid h-100 w-100"
            style="object-fit: cover; border-radius: 0.375rem 0 0 0.375rem"
          />
        </a>
        <a
          v-else
          class="d-flex align-items-center justify-content-center bg-gray h-100"
          :href="item.link"
          style="border-radius: 0.375rem 0 0 0.375rem"
        >
          <img
            src="@/assets/images/comses-logo-small.png"
            alt="Model image"
            class="img-fluid"
            style="max-width: 7rem; opacity: 0.2"
          />
        </a>
      </div>
      <div class="flex-grow-1 d-flex flex-column p-3">
        <h5 class="mb-2">
          <a :href="item.link" class="text-decoration-none feed-title">{{ item.title }}</a>
        </h5>
        <div class="d-flex align-items-start justify-content-between mt-auto">
          <small class="text-muted">
            <b v-if="item.author">
              {{ item.author }}
            </b>
            <span v-if="item.date && props.datePrefix">
              <span v-if="item.author"> • </span>
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
          </small>
          <a
            v-if="item.doi"
            class="badge bg-info ms-2 align-self-end"
            :href="`https://doi.org/${item.doi}`"
          >
            {{ item.doi }}
          </a>
        </div>
      </div>
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
