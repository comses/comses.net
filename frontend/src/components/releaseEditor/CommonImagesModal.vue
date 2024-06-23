<template>
  <button type="button" :class="buttonClass" data-cy="add image" rel="nofollow" @click="imagesModal?.show()">
    <i class="fas fa-image"></i> Add Images
  </button>
  <BootstrapModal id="images-modal" title="Upload Images" ref="imagesModal" size="lg" centered>
    <template #body>
      <div>
        <FileUpload
          accepted-file-types="image/gif, image/jpeg, image/png"
          title="Upload Images"
          :upload-url="uploadUrl"
          instructions="Upload media files here. Images are displayed on the detail page of every release for this codebase. GIF, JPEG and PNG files only."
          :originals="files"
          category="image"
          @delete-file="handleDeleteFile"
          @clear="handleClear"
          @upload-done="getMediaFiles"
        />
      </div>
    </template>
  </BootstrapModal>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import type Modal from "bootstrap/js/dist/modal";
import BootstrapModal from "@/components/BootstrapModal.vue";
import FileUpload from "@/components/releaseEditor/FileUpload.vue";
import { useCodebaseAPI } from "@/composables/api";
import { useReleaseEditorStore } from "@/stores/releaseEditor";
import type { FileInfo } from "@/types";

const props = defineProps<{
  buttonClass: string;
  identifier: string;
  files: FileInfo[];
}>();

const store = useReleaseEditorStore();

const imagesModal = ref<Modal>();

const { mediaListUrl, mediaDelete, mediaClear } = useCodebaseAPI();

const uploadUrl = computed(() => mediaListUrl(props.identifier));

async function getMediaFiles() {
  await store.fetchMediaFiles();
}

async function handleDeleteFile(imageId: string) {
  await mediaDelete(props.identifier, imageId);
  return getMediaFiles();
}

async function handleClear() {
  await mediaClear(props.identifier);
  return getMediaFiles();
}
</script>
