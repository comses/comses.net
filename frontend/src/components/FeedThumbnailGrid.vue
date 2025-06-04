<template>
  <!-- loading placeholder -->
  <div v-if="loading" class="row g-3 mb-4">
    <div v-for="n in props.limit" :key="`placeholder-${n}`" class="col-6">
      <div class="activity border rounded p-3 h-100 d-flex flex-column">
        <div class="text-center mb-3">
          <div class="placeholder bg-gray rounded" style="width: 100%; height: 120px"></div>
        </div>
        <div class="flex-grow-1 d-flex flex-column">
          <div class="mb-2">
            <span class="placeholder col-10"></span>
          </div>
          <div class="mt-auto">
            <small class="text-muted">
              <span class="placeholder col-5"></span>
            </small>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- actual content -->
  <div v-else class="row g-3 mb-4">
    <div v-for="item in items" :key="item.title" class="col-6">
      <div class="activity border rounded p-3 h-100 d-flex flex-column">
        <div class="text-center mb-3">
          <a :href="item.link">
            <img
              :src="item.thumbnail"
              :alt="item.title"
              class="img-fluid rounded"
              style="width: 100%; object-fit: cover"
            />
          </a>
        </div>
        <div class="flex-grow-1 d-flex flex-column">
          <div>
            <a :href="item.link" class="text-decoration-none feed-title">{{ item.title }}</a>
          </div>
          <div class="mt-auto">
            <small class="text-muted">
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
            </small>
          </div>
        </div>
      </div>
    </div>
  </div>
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
