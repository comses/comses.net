<template>
  <button
    type="button"
    class="btn btn-primary"
    :class="{ disabled: disabled }"
    rel="nofollow"
    @click="editContributorModal.show()"
  >
    <i class="fas fa-plus-square me-1"></i> Add a Contributor
  </button>
  <BootstrapModal
    v-if="!disabled"
    id="add-contributor-modal"
    title="Add a Contributor"
    ref="editContributorModal"
    size="lg"
    centered
  >
    <template #content>
      <div class="modal-body pb-0">
        <div v-if="!showCustomInput" class="d-flex align-items-end justify-content-between mb-3">
          <div class="flex-grow-1">
            <ReleaseEditorContributorSearch @select="populateFromContributor($event)" />
          </div>
          <div class="text-center mb-2 mx-3">
            <small class="text-muted">OR</small>
          </div>
          <div>
            <div class="text-center">
              <button
                type="button"
                class="btn btn-outline-secondary w-100"
                @click="showCustomInput = true"
              >
                <i class="fas fa-plus"></i> Create a New Contributor
              </button>
            </div>
          </div>
        </div>
        <button
          v-else
          type="button"
          class="btn btn-outline-secondary mb-3"
          @click="showCustomInput = false"
        >
          <i class="fas fa-angle-left me-1"></i> Search for Existing Contributors
        </button>
      </div>
      <ReleaseEditorContributorEditForm
        id="add-contributor-form"
        :show-custom-input="showCustomInput"
        ref="editFormRef"
        @success="() => editContributorModal.hide()"
      />
    </template>
  </BootstrapModal>
</template>
<script setup lang="ts">
import { ref } from "vue";
import type { Modal } from "bootstrap";
import BootstrapModal from "@/components/BootstrapModal.vue";
import ReleaseEditorContributorSearch from "@/components/ReleaseEditorContributorSearch.vue";
import ReleaseEditorContributorEditForm from "@/components/ReleaseEditorContributorEditForm.vue";
import type { Contributor } from "@/types";

const props = withDefaults(
  defineProps<{
    disabled?: boolean;
  }>(),
  {
    disabled: false,
  }
);

const editContributorModal = ref<typeof Modal>();
const editFormRef = ref<InstanceType<typeof ReleaseEditorContributorEditForm> | null>(null);

const showCustomInput = ref(false);

function populateFromContributor(contributor: Contributor) {
  if (editFormRef.value) {
    editFormRef.value.populateFromContributor(contributor);
  }
}
</script>
