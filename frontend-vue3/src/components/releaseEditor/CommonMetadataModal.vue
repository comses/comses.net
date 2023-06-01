<template>
  <button type="button" :class="buttonClass" rel="nofollow" @click="editCodebaseModal.show()">
    <i class="fas fa-edit"></i> Edit Common Metadata
  </button>
  <BootstrapModal
    id="edit-codebase-modal"
    title="Edit Common Metadata"
    ref="editCodebaseModal"
    size="lg"
    centered
  >
    <template #body>
      <CodebaseEditForm
        :codebase-id="identifier"
        id="edit-common-metadata-form"
        @success="editCodebaseModal.hide()"
        as-modal
      />
    </template>
    <template #footer>
      <button type="button" class="btn btn-outline-gray" data-bs-dismiss="modal">Cancel</button>
      <button type="submit" class="btn btn-primary" form="edit-common-metadata-form">Save</button>
    </template>
  </BootstrapModal>
</template>

<script setup lang="ts">
import { ref } from "vue";
import type { Modal } from "bootstrap";
import BootstrapModal from "@/components/BootstrapModal.vue";
import CodebaseEditForm from "@/components/CodebaseEditForm.vue";

const props = defineProps<{
  buttonClass: string;
  identifier: string;
}>();

const editCodebaseModal = ref<typeof Modal>();
</script>
