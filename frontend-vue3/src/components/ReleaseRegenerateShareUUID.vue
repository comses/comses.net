<template>
  <div class="input-group my-3">
    <button type="button" class="btn btn-outline-gray">
      <i class="fas fa-sync-alt" @click="regenerateShareUuid"></i>
    </button>
    <input id="release-share-url" readonly class="form-control bg-light" :value="shareUrl" />
    <button
      type="button"
      class="btn btn-outline-gray btn-clipboard"
      data-clipboard-target="#release-share-url"
      title="Copy to clipboard"
    >
      <i class="fas fa-copy"></i> Copy
    </button>
  </div>
</template>

<script setup lang="ts">
import { useReleaseAPI } from "@/composables/api/codebase";
import { ref } from "vue";

export interface RegenerateShareUUIDProps {
  identifier: string;
  versionNumber: string;
  initialShareUrl: string;
}

const props = defineProps<RegenerateShareUUIDProps>();

const shareUrl = ref(props.initialShareUrl);

const { regenerateShareUUID, data } = useReleaseAPI();

async function regenerateShareUuid() {
  await regenerateShareUUID(props.identifier, props.versionNumber);
  if (data.value && typeof data.value === "string") {
    shareUrl.value = data.value;
  }
}
</script>
