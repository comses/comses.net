<template>
  <button
    type="button"
    :class="buttonClass"
    data-cy="add-media"
    rel="nofollow"
    @click="mediaModal?.show()"
  >
    <i class="fas fa-photo-video"></i> Add Media
  </button>
  <BootstrapModal id="media-modal" title="Media" ref="mediaModal" size="lg" centered>
    <template #body>
      <div>
        <form class="mb-4" @submit="handleVideoSubmit">
          <TextField
            name="videoSourceUrl"
            label="Video URL (optional)"
            help="If provided, this video appears alongside images on the codebase detail page."
          />
          <div class="mt-2 d-flex align-items-center gap-2">
            <button type="submit" class="btn btn-outline-primary btn-sm" :disabled="isSavingVideo">
              Save video
            </button>
            <small v-if="videoSaveMessage" class="text-muted">{{ videoSaveMessage }}</small>
          </div>
        </form>
        <FileUpload
          accepted-file-types="image/gif, image/jpeg, image/png"
          title="Upload Images"
          :upload-url="uploadUrl"
          instructions="Upload image files here. Images are displayed on the detail page of every release for this codebase. GIF, JPEG and PNG files only."
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
import * as yup from "yup";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import type Modal from "bootstrap/js/dist/modal";
import BootstrapModal from "@/components/BootstrapModal.vue";
import FileUpload from "@/components/releaseEditor/FileUpload.vue";
import TextField from "@/components/form/TextField.vue";
import { useCodebaseAPI } from "@/composables/api";
import { useForm } from "@/composables/form";
import { useReleaseEditorStore } from "@/stores/releaseEditor";
import type { FileInfo } from "@/types";

const props = defineProps<{
  buttonClass: string;
  identifier: string;
  files: FileInfo[];
  show: boolean;
}>();

const store = useReleaseEditorStore();

const mediaModal = ref<Modal>();

const { data, mediaListUrl, mediaDelete, mediaClear, retrieve, partialUpdate } = useCodebaseAPI();

const uploadUrl = computed(() => mediaListUrl(props.identifier));

const videoSaveMessage = ref<string>("");
const isSavingVideo = ref(false);

/** Matches common YouTube watch, embed, shorts, and youtu.be URLs (optional field: empty allowed). */
const youtubeUrlRegex =
  /^(?:https?:\/\/)?(?:m\.)?(?:youtu\.be\/|www\.youtube\.com\/(?:watch\?v=|embed\/|v\/|shorts\/|.*[?&]v=))([a-zA-Z0-9_-]{11})(?:\S*)?$/;

const youtubeSchema = yup.object().shape({
  videoSourceUrl: yup.string().test("youtube-or-empty", "Must be a valid YouTube URL", value => {
    if (!value || value.trim() === "") return true;
    return youtubeUrlRegex.test(value.trim());
  }),
});

type VideoFields = yup.InferType<typeof youtubeSchema>;

const {
  handleSubmit,
  values,
  setValuesWithLoadTime,
  addUnsavedAlertListener,
  removeUnsavedAlertListener,
} = useForm<VideoFields>({
  schema: youtubeSchema,
  initialValues: {
    videoSourceUrl: "",
  },
  onSubmit: async () => {
    isSavingVideo.value = true;
    videoSaveMessage.value = "";
    try {
      await partialUpdate(props.identifier, { videoSourceUrl: values.videoSourceUrl });
      await store.fetchCodebaseRelease(props.identifier, store.release.versionNumber);
      videoSaveMessage.value = "Saved.";
    } finally {
      isSavingVideo.value = false;
    }
  },
});

const handleVideoSubmit = handleSubmit;

onMounted(async () => {
  if (props.show) {
    mediaModal.value?.show();
  }
  if (props.identifier) {
    await retrieve(props.identifier);
    setValuesWithLoadTime(data.value);
  }
  addUnsavedAlertListener();
});

onBeforeUnmount(() => {
  removeUnsavedAlertListener();
});

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
