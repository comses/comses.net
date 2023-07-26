<template>
  <div>
    <div
      class="w-100 mb-3 d-flex justify-content-between border rounded gallery-frame"
      :class="{ fixed }"
    >
      <button
        v-if="images.length > 1"
        class="btn btn-link position-relative fs-2"
        :disabled="activeImageIndex === 0"
        @click="setActiveIndex(activeImageIndex - 1)"
        role="button"
        aria-label="Previous Image"
      >
        <i class="fas fa-chevron-left"></i>
      </button>
      <div class="flex-grow-1 mx-2 overflow-hidden d-flex justify-content-center">
        <img
          :src="activeImage"
          class="active-gallery-img"
          @click="activeImageModal?.show()"
          role="button"
          alt="Selected Image"
          aria-label="Selected Image"
        />
      </div>
      <button
        v-if="images.length > 1"
        class="btn btn-link position-relative fs-2"
        :disabled="activeImageIndex === images.length - 1"
        @click="setActiveIndex(activeImageIndex + 1)"
        role="button"
        aria-label="Next Image"
      >
        <i class="fas fa-chevron-right"></i>
      </button>
    </div>
    <div v-if="images.length > 1" class="d-flex flex-wrap justify-content-center">
      <img
        v-for="(img, index) in images"
        :key="index"
        :src="img"
        class="gallery-img-thumbnail me-3"
        :class="img === activeImage ? 'active' : ''"
        @click="setActiveIndex(index)"
        role="listitem button"
        alt="Gallery Thumbnail Image"
        aria-label="Gallery Thumbnail Image"
      />
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
        <div class="d-flex justify-content-center">
          <img :src="activeImage" class="img-fluid" alt="Full Size Image" />
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
}

const props = withDefaults(defineProps<ImageGalleryProps>(), {
  title: "",
  fixed: true,
});

const activeImageIndex = ref(0);
const activeImageModal = ref<Modal>();

const activeImage = computed(() => props.images[activeImageIndex.value]);

function setActiveIndex(index: number) {
  if (index < 0 || index >= props.images.length) return;
  activeImageIndex.value = index;
}
</script>
