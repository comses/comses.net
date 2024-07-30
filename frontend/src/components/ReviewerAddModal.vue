<template>
  <button
    type="button"
    class="btn btn-primary"
    rel="nofollow"
    @click="
      addFormRef?.resetForm();
      addReviewerModal?.show();
    "
  >
    <i class="fas fa-plus-square me-1"></i> Add a Reviewer
  </button>
  <BootstrapModal
    id="add-reviewer-modal"
    title="Add a Reviewer"
    ref="addReviewerModal"
    size="lg"
    centered
  >
    <template #content>
      <ReviewerEditForm
        id="add-reviewer-form"
        :is-edit="false"
        ref="addFormRef"
        @success="() => addReviewerModal?.hide()"
      />
    </template>
  </BootstrapModal>
</template>
<script setup lang="ts">
import { ref } from "vue";
import type Modal from "bootstrap/js/dist/modal";
import BootstrapModal from "@/components/BootstrapModal.vue";
import ReviewerEditForm from "@/components/ReviewerEditForm.vue";

const addReviewerModal = ref<Modal>();
const addFormRef = ref<InstanceType<typeof ReviewerEditForm> | null>(null);
</script>
