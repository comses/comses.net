<template>
  <div>
    <div
      class="w-100 mb-3 d-flex justify-content-between border rounded gallery-frame"
      :class="{ fixed }"
    >
      <button
        v-if="mediaItems.length > 1"
        class="btn btn-link position-relative fs-2"
        :disabled="activeIndex === 0"
        @click="setActiveIndex(activeIndex - 1)"
        role="button"
        aria-label="Previous Media"
      >
        <i class="fas fa-chevron-left"></i>
      </button>
      <div class="flex-grow-1 mx-2 overflow-hidden d-flex justify-content-center">
        <img
          v-if="activeItem?.type === 'image'"
          :src="activeItem.src"
          class="active-gallery-img"
          @click="activeImageModal?.show()"
          role="button"
          alt="Selected Image"
          aria-label="Selected Image"
        />
        <div
          v-else-if="activeItem?.type === 'video'"
          class="gallery-video-preview position-relative w-100 ratio ratio-16x9 rounded overflow-hidden"
          role="button"
          tabindex="0"
          aria-label="Open video to watch"
          @click="activeImageModal?.show()"
          @keydown.enter.prevent="activeImageModal?.show()"
          @keydown.space.prevent="activeImageModal?.show()"
        >
          <img
            v-if="videoThumbnailUrl"
            :src="videoThumbnailUrl"
            class="w-100 h-100 object-fit-cover"
            alt="Video thumbnail"
          />
          <div
            v-else
            class="w-100 h-100 d-flex align-items-center justify-content-center bg-dark text-white"
          >
            Video
          </div>
          <div
            class="position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center gallery-video-preview-overlay"
          >
            <i class="fas fa-play-circle gallery-video-play-icon" aria-hidden="true"></i>
          </div>
        </div>
      </div>
      <button
        v-if="mediaItems.length > 1"
        class="btn btn-link position-relative fs-2"
        :disabled="activeIndex === mediaItems.length - 1"
        @click="setActiveIndex(activeIndex + 1)"
        role="button"
        aria-label="Next Media"
      >
        <i class="fas fa-chevron-right"></i>
      </button>
    </div>
    <div v-if="mediaItems.length > 1" class="d-flex flex-wrap justify-content-center">
      <template v-for="(item, index) in mediaItems" :key="index">
        <img
          v-if="item.type === 'image'"
          :src="item.src"
          class="gallery-img-thumbnail me-3"
          :class="index === activeIndex ? 'active' : ''"
          @click="setActiveIndex(index)"
          role="listitem button"
          alt="Gallery Thumbnail Image"
          aria-label="Gallery Thumbnail Image"
        />
        <div
          v-else
          class="gallery-img-thumbnail me-3 d-flex align-items-center justify-content-center position-relative"
          :class="index === activeIndex ? 'active' : ''"
          @click="setActiveIndex(index)"
          role="listitem button"
          aria-label="Gallery Video Thumbnail"
        >
          <div class="ratio ratio-16x9 w-100">
            <img
              v-if="videoThumbnailUrl"
              :src="videoThumbnailUrl"
              class="w-100 h-100 object-fit-cover"
              alt="Video Thumbnail"
            />
            <div
              v-else
              class="w-100 h-100 d-flex align-items-center justify-content-center bg-dark text-white"
            >
              Video
            </div>
          </div>
          <i
            class="fas fa-play-circle position-absolute gallery-video-play-icon gallery-video-play-icon--small"
            aria-hidden="true"
          ></i>
        </div>
      </template>
    </div>
    <BootstrapModal
      id="active-image-modal"
      ref="activeImageModal"
      :title="title ?? ''"
      size="xl"
      image
      centered
    >
      <template #body>
        <div class="d-flex justify-content-center w-100">
          <img
            v-if="activeItem?.type === 'image'"
            :src="activeItem.src"
            class="img-fluid"
            alt="Full Size Image"
          />
          <div v-else-if="activeItem?.type === 'video'" class="ratio ratio-16x9 w-100">
            <iframe
              v-if="videoEmbedUrl"
              referrerpolicy="strict-origin-when-cross-origin"
              :src="videoEmbedUrl"
              title="YouTube video player"
              frameborder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowfullscreen
            ></iframe>
          </div>
        </div>
      </template>
    </BootstrapModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import type Modal from "bootstrap/js/dist/modal";
import BootstrapModal from "@/components/BootstrapModal.vue";

export interface ImageGalleryProps {
  images: string[];
  title?: string;
  fixed?: boolean;
  videoUrl?: string;
}

const props = withDefaults(defineProps<ImageGalleryProps>(), {
  title: "",
  fixed: true,
  videoUrl: undefined,
});

type MediaItem = {
  type: "image" | "video";
  src: string;
};

const mediaItems = computed<MediaItem[]>(() => {
  const items: MediaItem[] = props.images.map(src => ({ type: "image", src }));
  if (props.videoUrl) {
    items.unshift({ type: "video", src: props.videoUrl });
  }
  return items;
});

const activeIndex = ref(0);
const activeImageModal = ref<Modal>();

const activeItem = computed(() => mediaItems.value[activeIndex.value]);

function setActiveIndex(index: number) {
  if (index < 0 || index >= mediaItems.value.length) return;
  activeIndex.value = index;
}

function getYouTubeId(url: string): string | null {
  const match = url.match(
    /(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|embed\/|v\/|shorts\/|.*[?&]v=))([a-zA-Z0-9_-]{11})/
  );
  return match ? match[1] : null;
}

const videoId = computed(() => (props.videoUrl ? getYouTubeId(props.videoUrl) : null));

const videoEmbedUrl = computed(() =>
  videoId.value ? `https://www.youtube.com/embed/${videoId.value}` : null
);

const videoThumbnailUrl = computed(() =>
  videoId.value ? `https://img.youtube.com/vi/${videoId.value}/hqdefault.jpg` : null
);
</script>

<style scoped>
.gallery-video-preview:focus-visible {
  outline: 2px solid var(--bs-primary, #0d6efd);
  outline-offset: 2px;
}

.gallery-video-preview-overlay {
  pointer-events: none;
  background: rgba(0, 0, 0, 0.12);
}

.gallery-video-play-icon {
  color: #6c757d;
  font-size: 4rem;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.35));
}

.gallery-video-play-icon--small {
  font-size: 2rem;
}
</style>
