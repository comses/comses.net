<template>
  <div>
    <h3 :class="category === 'package' ? 'mt-0' : 'mt-4'">{{ title }}</h3>
    <slot name="label"></slot>
    <div class="text-muted mb-1" v-if="instructions">{{ instructions }}</div>
    <div
      class="mb-3"
      @dragenter.prevent="dragDepth++"
      @dragover.prevent
      @dragleave.prevent="dragDepth = Math.max(0, dragDepth - 1)"
      @drop.prevent="handleDrop"
    >
      <button
        type="button"
        class="upload-dropzone w-100 rounded p-4 my-2 text-center"
        :class="{ 'is-dragging': dragDepth > 0 && !uploading }"
        :data-cy="`dropzone-${category}`"
        :disabled="uploading"
        @click="fileInput?.click()"
      >
        <span class="fas fa-cloud-upload-alt d-block fs-3 mb-2" aria-hidden="true"></span>
        <span class="fw-semibold">{{ uploading ? "Uploading files…" : "Drop files here" }}</span>
        <span class="d-block small mt-1">{{
          uploading ? "You can add more when this upload finishes" : "or click to browse"
        }}</span>
      </button>
      <input
        ref="fileInput"
        class="d-none"
        :data-cy="`upload-${category}`"
        type="file"
        @change="handleFiles"
        :accept="acceptedFileTypes"
        :disabled="uploading"
        multiple
      />
    </div>
    <div v-if="totalFiles" class="alert alert-secondary" :data-cy="`upload-status-${category}`">
      <div role="status" aria-live="polite" class="text-break" :class="{ 'mb-2': uploading }">
        <template v-if="uploading">
          {{ completedFiles + 1 }} of {{ totalFiles }} —
          {{ fileProgress === 100 ? "Processing" : "Uploading" }} {{ currentFile }}
        </template>
        <template v-else>
          {{ successfulFiles }} of {{ totalFiles }}
          {{ totalFiles === 1 ? "file" : "files" }} uploaded<span v-if="uploadErrors.length"
            >; see errors below</span
          >.
        </template>
      </div>
      <div v-if="uploading" class="progress" style="height: 6px">
        <div
          class="progress-bar"
          role="progressbar"
          aria-label="Upload progress"
          :aria-valuenow="progress"
          aria-valuemin="0"
          aria-valuemax="100"
          :style="{ width: `${progress}%` }"
        ></div>
      </div>
    </div>
    <div class="alert alert-danger text-break" v-if="uploadErrors.length" role="alert">
      <div v-for="(error, index) in uploadErrors" :key="index">{{ error }}</div>
    </div>
    <button
      v-if="originals.length"
      type="button"
      class="btn btn-sm btn-danger mb-2"
      :disabled="uploading"
      @click="emit('clear')"
    >
      Remove all files
    </button>
    <div class="list-group" v-if="!hideFileList && originals.length > 0">
      <div
        class="list-group-item d-flex justify-content-between align-items-center"
        v-for="file in originals"
        :key="file.identifier"
      >
        {{ file.name }}
        <button
          class="btn btn-sm btn-danger float-end"
          @click="emit('deleteFile', file.identifier)"
        >
          <span class="fas fa-trash-alt"></span>
        </button>
      </div>
    </div>
    <div class="alert alert-info" v-else-if="!hideFileList">No files uploaded</div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useReleaseEditorAPI } from "@/composables/api";

export interface FileUploadProps {
  title: string;
  instructions: string;
  uploadUrl: string;
  acceptedFileTypes: string;
  category: string;
  hideFileList?: boolean;
  originals: { name: string; identifier: string }[];
}

const props = withDefaults(defineProps<FileUploadProps>(), {
  instructions: "",
  acceptedFileTypes: "",
});

const emit = defineEmits<{
  (e: "deleteFile", identifier: string): void;
  (e: "clear"): void;
  (e: "uploadDone"): void;
}>();

const { uploadFile, serverErrors } = useReleaseEditorAPI();
const uploadErrors = ref<string[]>([]);
const fileInput = ref<HTMLInputElement | null>(null);
const dragDepth = ref(0);
const uploading = ref(false);
const totalFiles = ref(0);
const completedFiles = ref(0);
const successfulFiles = ref(0);
const currentFile = ref("");
const fileProgress = ref(0);
const progress = computed(() =>
  totalFiles.value
    ? Math.round(((completedFiles.value + fileProgress.value / 100) / totalFiles.value) * 100)
    : 0
);

function handleFiles(event: Event) {
  const input = event.target as HTMLInputElement;
  const files = Array.from(input.files || []);
  input.value = "";
  uploadFiles(files);
}

function handleDrop(event: DragEvent) {
  dragDepth.value = 0;
  if (uploading.value || !event.dataTransfer) return;
  const items = Array.from(event.dataTransfer.items);
  if (items.some(item => item.webkitGetAsEntry?.()?.isDirectory)) {
    uploadErrors.value = ["Please upload folders as a ZIP or tar archive."];
    return;
  }
  uploadFiles(Array.from(event.dataTransfer.files));
}

async function uploadFiles(files: File[]) {
  if (uploading.value || !files.length) return;
  uploading.value = true;
  uploadErrors.value = [];
  totalFiles.value = files.length;
  completedFiles.value = 0;
  successfulFiles.value = 0;
  for (const file of files) {
    currentFile.value = file.name;
    fileProgress.value = 0;
    try {
      await uploadFile(
        props.uploadUrl,
        file,
        event => {
          fileProgress.value = event.total
            ? Math.min(100, Math.round((event.loaded * 100) / event.total))
            : 0;
        },
        () => {}
      );
      if (!serverErrors.value.length) {
        successfulFiles.value++;
        emit("uploadDone");
      }
    } catch {
      // The API composable supplies the error message, including network failures.
    } finally {
      uploadErrors.value.push(...serverErrors.value.map(message => `${file.name}: ${message}`));
      completedFiles.value++;
    }
  }
  uploading.value = false;
}
</script>

<style scoped>
.upload-dropzone {
  border: 2px dashed var(--bs-secondary);
  background: var(--bs-light);
  color: var(--bs-body-color);
  transition:
    border-color 0.15s,
    background-color 0.15s;
}

.upload-dropzone:not(:disabled):hover,
.upload-dropzone:focus-visible,
.upload-dropzone.is-dragging {
  border-color: var(--bs-primary);
  background: var(--bs-primary-bg-subtle, #edf4fa);
}

.upload-dropzone:disabled {
  opacity: 0.65;
}
</style>
