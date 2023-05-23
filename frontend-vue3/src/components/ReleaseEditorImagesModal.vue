<template>
  <button type="button" :class="buttonClass" rel="nofollow" @click="imagesModal.show()">
    <i class="fas fa-image"></i> Add Images
  </button>
  <BootstrapModal id="images-modal" title="Upload Images" ref="imagesModal" centered>
    <template #body> TODO: images form </template>
  </BootstrapModal>
</template>

<script setup lang="ts">
import { ref } from "vue";
import type { Modal } from "bootstrap";
import BootstrapModal from "@/components/BootstrapModal.vue";

const props = defineProps<{
  buttonClass: string;
}>();

const imagesModal = ref<typeof Modal>();
</script>
