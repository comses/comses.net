<template>
  <ReviewerCard
    v-if="reviewer"
    :reviewer="reviewer"
    @edit="
      editForm?.resetForm();
      editModal?.show();
    "
    @changeActiveState="r => emit('update', r)"
  />
  <button
    v-else-if="reviewer === null"
    type="button"
    class="btn btn-primary mb-3"
    rel="nofollow"
    @click="
      addForm?.resetForm();
      addModal?.show();
    "
  >
    <i class="fas fa-plus-square me-1"></i> Create Peer Reviewer Profile
  </button>
  <BootstrapModal id="add-modal" title="Create Reviewer Profile" ref="addModal" size="lg" centered>
    <template #content>
      <ReviewerEditForm
        id="add-reviewer-form"
        ref="addForm"
        :memberProfile="memberProfile"
        :isEdit="false"
        @success="
          r => {
            emit('update', r);
            addModal?.hide();
          }
        "
      />
    </template>
  </BootstrapModal>
  <BootstrapModal
    v-if="reviewer"
    id="edit-modal"
    title="Edit Reviewer Profile"
    ref="editModal"
    size="lg"
    centered
  >
    <template #content>
      <ReviewerEditForm
        id="edit-reviewer-form"
        ref="editForm"
        :isEdit="true"
        :reviewer="reviewer"
        @success="
          r => {
            emit('update', r);
            editModal?.hide();
          }
        "
      />
    </template>
  </BootstrapModal>
</template>

<script setup lang="ts">
import { ref } from "vue";
import BootstrapModal from "@/components/BootstrapModal.vue";
import ReviewerCard from "./ReviewerCard.vue";
import ReviewerEditForm from "@/components/ReviewerEditForm.vue";
import type { RelatedMemberProfile, Reviewer } from "@/types";

const props = defineProps<{
  reviewer?: Reviewer | null;
  memberProfile?: RelatedMemberProfile;
}>();

const emit = defineEmits<{
  update: [Reviewer];
}>();

const addForm = ref<InstanceType<typeof ReviewerEditForm> | null>(null);
const addModal = ref<InstanceType<typeof BootstrapModal> | null>(null);
const editForm = ref<InstanceType<typeof ReviewerEditForm> | null>(null);
const editModal = ref<InstanceType<typeof BootstrapModal> | null>(null);
</script>
