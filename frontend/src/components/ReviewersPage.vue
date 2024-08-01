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
              editForm?.resetForm();
              editModal?.show();
            "
            >Edit</a
          >
          <a class="btn btn-danger" @click="deleteReviewer(reviewer)">Delete</a>
        </div>
      </div>
    </div>
    <div class="col-sm-12 col-md-3">
      <button
        type="button"
        class="btn btn-primary"
        rel="nofollow"
        @click="
          addForm?.resetForm();
          addModal?.show();
        "
      >
        <i class="fas fa-plus-square me-1"></i> Add a Reviewer
      </button>
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
          ref="editForm"
          :is-edit="true"
          :reviewer="editCandidate"
          @success="
            async () => {
              await retrieveReviewers();
              editModal?.hide();
            }
          "
        />
      </template>
    </BootstrapModal>
    <BootstrapModal id="add-reviewer-modal" title="Add Reviewer" ref="addModal" size="lg" centered>
      <template #content>
        <ReviewerEditForm
          id="add-reviewer-form"
          :is-edit="false"
          ref="addForm"
          @success="
            async () => {
              await retrieveReviewers();
              addModal?.hide();
            }
          "
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
import type { Reviewer } from "@/types";

const reviewers = ref<Reviewer[]>([]);
const addForm = ref<InstanceType<typeof ReviewerEditForm> | null>(null);
const addModal = ref<InstanceType<typeof BootstrapModal> | null>(null);
const editForm = ref<InstanceType<typeof ReviewerEditForm> | null>(null);
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
