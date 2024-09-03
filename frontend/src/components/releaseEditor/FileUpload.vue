<template>
  <div>
    <h3 class="mt-4">{{ title }}</h3>
    <slot name="label"></slot>
    <div class="text-muted mb-1" v-if="instructions">{{ instructions }}</div>
    <div class="d-flex justify-content-between mb-2">
      <div>
        <label :for="uploadId"><div class="btn btn-primary">Upload a file</div></label>
        <input
          class="invisible"
          :data-cy="`upload-${category}`"
          :id="uploadId"
          type="file"
          @change="handleFiles($event)"
          :accept="acceptedFileTypes"
          multiple
        />
      </div>
      <div>
        <button v-if="originals.length" class="btn btn-danger" @click="emit('clear')">
          Remove all files
        </button>
      </div>
    </div>
    <div>
      <div class="alert alert-secondary" v-for="(info, name) in fileUploadProgress" :key="name">
        File upload {{ name }} is <b>{{ info.percentCompleted }}%</b> complete
      </div>
      <div class="alert alert-danger alert-dismissable" v-if="hasErrors">
        <button class="btn-close" aria-label="Close" @click="clearUploadErrors"></button>
        <div v-if="fileUploadErrors.detail">
          {{ fileUploadErrors.detail }}
        </div>
        <div v-else v-for="(error, name) in fileUploadErrors" :key="name">
          <div v-for="msg in error.msgs" :key="msg.msg.detail">
            <b>{{ displayStage(msg.msg.stage) }}</b
            >: {{ msg.msg.detail }}
          </div>
        </div>
      </div>
    </div>
    <div class="list-group" v-if="originals.length > 0">
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
    <div class="alert alert-info" v-else>No files uploaded</div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { delay, isEmpty, uniqueId } from "lodash-es";
import { useReleaseEditorAPI } from "@/composables/api";
import type { UploadFailure, UploadProgress } from "@/types";

export interface FileUploadProps {
  title: string;
  instructions: string;
  uploadUrl: string;
  acceptedFileTypes: string;
  category: string;
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

const { uploadFile } = useReleaseEditorAPI();

const fileUploadErrors = ref<{ [name: string]: UploadFailure }>({});
const fileUploadProgress = ref<{ [name: string]: UploadProgress }>({});

const uploadId = computed(() => `upload_${uniqueId()}`);
const hasErrors = computed(() => !isEmpty(fileUploadErrors.value));

function displayStage(stage: string) {
  return stage === "sip" ? "During archive unpack" : "During upload";
}

function clearUploadErrors() {
  fileUploadErrors.value = {};
}

async function handleFiles(event: Event) {
  const inputEl = event.target as HTMLInputElement;
  if (!inputEl.files) return;

  for (const file of inputEl.files) {
    delay(() => delete fileUploadProgress.value[file.name], 6000);
    await uploadFile(
      props.uploadUrl,
      file,
      progressEvent => {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / (progressEvent.total || 1)
        );
        fileUploadProgress.value[file.name] = {
          kind: "progress",
          percentCompleted,
          size: file.size,
        };
      },
      error => {
        if (error.response) {
          const data = error.response.data as any;
          if (data.detail) {
            fileUploadErrors.value = data;
          } else {
            fileUploadErrors.value[file.name] = {
              kind: "failure",
              msgs: data,
            };
          }
        }
      }
    );
    inputEl.value = "";
    emit("uploadDone");
  }
}
</script>
