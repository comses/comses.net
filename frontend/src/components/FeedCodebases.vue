<template>
  <!-- loading placeholder -->
  <template v-if="loading">
    <div
      v-for="n in props.limit"
      :key="`placeholder-${n}`"
      class="activity border rounded p-3 mb-3"
    >
      <div class="d-flex">
        <div class="flex-shrink-0 me-3">
          <div class="placeholder bg-gray rounded" style="width: 100px; height: 100px"></div>
        </div>
        <div class="flex-grow-1 d-flex flex-column">
          <h5 class="mb-2">
            <span class="placeholder col-8 placeholder-lg"></span>
          </h5>
          <div class="d-flex align-items-start justify-content-between mt-auto">
            <small class="text-muted">
              <span class="placeholder col-6"></span>
              <br />
              <span class="placeholder col-4"></span>
            </small>
          </div>
        </div>
      </div>
    </div>
  </template>

  <!-- actual content -->
  <template v-else>
    <div v-for="item in items" :key="item.title" class="activity border rounded p-3 mb-3">
      <div class="d-flex">
        <div class="flex-shrink-0 me-3">
          <a v-if="item.thumbnail" class="position-relative" :href="item.link">
            <img
              :src="item.thumbnail"
              alt="Model image"
              class="img-fluid rounded"
              style="width: 100px; height: 100px; object-fit: cover"
            />
          </a>
          <a
            v-else
            class="d-flex align-items-center justify-content-center bg-gray rounded"
            style="width: 100px; height: 100px"
            :href="item.link"
          >
            <img
              src="@/assets/images/comses-logo-small.png"
              alt="Model image"
              class="img-fluid"
              style="max-width: 75px; opacity: 0.3"
            />
          </a>
        </div>
        <div class="flex-grow-1 d-flex flex-column">
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
.placeholder {
  opacity: 0.2;
}
</style>
