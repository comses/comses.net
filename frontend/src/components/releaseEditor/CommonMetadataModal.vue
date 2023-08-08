<template>
  <button type="button" :class="buttonClass" rel="nofollow" @click="editCodebaseModal?.show()">
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
        :identifier="identifier"
        id="edit-common-metadata-form"
        @success="handleSuccess()"
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
import type Modal from "bootstrap/js/dist/modal";
import BootstrapModal from "@/components/BootstrapModal.vue";
import CodebaseEditForm from "@/components/CodebaseEditForm.vue";
import { useReleaseEditorStore } from "@/stores/releaseEditor";

const props = defineProps<{
  buttonClass: string;
  identifier: string;
}>();

const editCodebaseModal = ref<Modal>();

const store = useReleaseEditorStore();

async function handleSuccess() {
  await store.initialize(store.identifier, store.versionNumber);
  editCodebaseModal.value?.hide();
}
</script>
