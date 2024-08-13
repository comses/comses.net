<template>
  <div class="row">
    <div class="col-sm-12 col-md-9">
      <ReviewerCard
        v-for="reviewer of filteredReviewers"
        :key="reviewer.id"
        :reviewer="reviewer"
        @edit="
          editCandidate = reviewer;
          editForm?.resetForm();
          editModal?.show();
        "
        @activate="changeReviwerActiveState(reviewer, true)"
        @deactivate="changeReviwerActiveState(reviewer, false)"
      />
    </div>
    <div class="col-sm-12 col-md-3">
      <ReviewersListSidebar
        @filter="
          values => {
            filters = values;
            applyFilters();
          }
        "
        @add-success="retrieveReviewers"
        :programming-languages="programmingLanguages"
      />
    </div>
    <BootstrapModal id="edit-modal" title="Edit Reviewer" ref="editModal" size="lg" centered>
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useReviewEditorAPI } from "@/composables/api";
import BootstrapModal from "@/components/BootstrapModal.vue";
import ReviewerCard from "./ReviewerCard.vue";
import ReviewerEditForm from "@/components/ReviewerEditForm.vue";
import ReviewersListSidebar from "./ReviewersListSidebar.vue";
import type { Reviewer, ReviewerFilterParams } from "@/types";

const allReviewers = ref<Reviewer[]>([]);
const filteredReviewers = ref<Reviewer[]>([]);
const filters = ref<ReviewerFilterParams>({ includeInactive: false });
const editForm = ref<InstanceType<typeof ReviewerEditForm> | null>(null);
const editModal = ref<InstanceType<typeof BootstrapModal> | null>(null);
const editCandidate = ref<Reviewer>();

const { updateReviewer: update, findReviewers } = useReviewEditorAPI();

onMounted(async () => {
  await retrieveReviewers();
});

async function retrieveReviewers() {
  const response = await findReviewers({});
  allReviewers.value = response.data.results;
  applyFilters();
}

function applyFilters() {
  let reviewers = allReviewers.value;
  const curFilters = filters.value;
  if (!curFilters.includeInactive) {
    reviewers = reviewers.filter(reviewer => reviewer.isActive);
  }
  if (curFilters.name) {
    reviewers = reviewers.filter(
      reviewer =>
        reviewer.memberProfile.name.toLowerCase().includes(curFilters.name!.toLowerCase()) ||
        reviewer.memberProfile.username.toLowerCase().includes(curFilters.name!.toLowerCase())
    );
  }
  if (curFilters.programmingLanguages?.length) {
    reviewers = reviewers.filter(reviewer =>
      curFilters.programmingLanguages!.some(language =>
        reviewer.programmingLanguages.includes(language)
      )
    );
  }
  filteredReviewers.value = reviewers;
}

async function changeReviwerActiveState(reviewer: Reviewer, isActive: boolean) {
  // FIXME: Make server accept partial reviewer object without defining memberProfileId
  await update(reviewer.id, { memberProfileId: reviewer.memberProfile.id, isActive });
  await retrieveReviewers();
}

const programmingLanguages = computed(() => {
  const languages = new Set<string>();
  for (const reviewer of allReviewers.value) {
    for (const language of reviewer.programmingLanguages) {
      languages.add(language);
    }
  }
  return [...languages];
});
</script>
