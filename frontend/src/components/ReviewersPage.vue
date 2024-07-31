<template>
  <div class="row">
    <div class="col-sm-12 col-md-9">
      <div v-for="reviewer of reviewers" :key="reviewer.id" class="card mb-3">
        <div class="card-header">
          <h5 class="card-title">{{ reviewer.memberProfile.name }}</h5>
        </div>
        <div class="card-body">
          <p class="card-text">
            <strong>Email:</strong> {{ reviewer.memberProfile.email }}<br />
            <strong>Programming Languages:</strong> {{ reviewer.programmingLanguages.join(", ")
            }}<br />
            <strong>Subject Areas:</strong> {{ reviewer.subjectAreas.join(", ") }}<br />
            {{ reviewer.notes }}
          </p>
          <a
            class="btn btn-primary"
            @click="
              editCandidate = reviewer;
              editFormRef?.resetForm();
              editModal?.show();
            "
            >Edit</a
          >
          <a class="btn btn-danger" @click="deleteReviewer(reviewer)">Delete</a>
        </div>
      </div>
    </div>
    <div class="col-sm-12 col-md-3">
      <ReviewerAddModal />
    </div>
    <BootstrapModal
      id="edit-reviewer-modal"
      title="Edit Reviewer"
      ref="editModal"
      size="lg"
      centered
    >
      <template #content>
        <ReviewerEditForm
          id="edit-reviewer-form"
          ref="editFormRef"
          :is-edit="true"
          :reviewer="editCandidate"
          @success="() => editModal?.hide()"
        />
      </template>
    </BootstrapModal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useReviewEditorAPI } from "@/composables/api";
import BootstrapModal from "@/components/BootstrapModal.vue";
import ReviewerEditForm from "@/components/ReviewerEditForm.vue";
import ReviewerAddModal from "@/components/ReviewerAddModal.vue";
import type { Reviewer } from "@/types";

const reviewers = ref<Reviewer[]>([]);
const editFormRef = ref<InstanceType<typeof ReviewerEditForm> | null>(null);
const editModal = ref<InstanceType<typeof BootstrapModal> | null>(null);
const editCandidate = ref<Reviewer>();

const { updateReviewer: update, findReviewers } = useReviewEditorAPI();

onMounted(async () => {
  await retrieveReviewers();
});

async function retrieveReviewers() {
  const response = await findReviewers({});
  reviewers.value = response.data.results;
}

async function deleteReviewer(reviewer: Reviewer) {
  // FIXME: Make server accept partial reviewer object without defining memberProfileId
  await update(reviewer.id, { memberProfileId: reviewer.memberProfile.id, isActive: false });
  await retrieveReviewers();
}
</script>
