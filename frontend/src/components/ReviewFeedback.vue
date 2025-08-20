<template>
  <div>
    <div class="container-fluid px-0" v-if="sortedFeedbackItems.length > 0">
      <div
        class="card mb-2 position-relative"
        v-for="feedback in sortedFeedbackItems"
        :key="feedback.dateCreated"
      >
        <div class="card-body py-2 px-3">
          <a v-if="!disabled" :href="feedback.editorUrl" class="stretched-link"></a>
          <div class="d-flex flex-column flex-md-row align-items-md-start gap-2">
            <div class="d-flex flex-column gap-1">
              <div v-if="feedback.recommendation">
                <a :href="feedback.editorUrl">{{ feedback.reviewerName }} recommended </a>
                <span class="badge" :class="`bg-${recommendationVariant(feedback.recommendation)}`">
                  {{ feedback.recommendation }}
                </span>
              </div>
              <div v-else>
                <span class="text-muted">{{ feedback.reviewerName }}'s feedback </span>
                <span class="badge bg-gray">draft</span>
              </div>
              <div v-if="isLatestNonDraft(feedback)">
                <span class="badge" :class="`bg-${reviewStatusVariant(feedback.reviewStatus)}`">
                  {{ feedback.reviewStatus }}
                </span>
              </div>
            </div>
            <div class="ms-md-auto">
              <span class="small text-muted">
                Updated <b>{{ new Date(feedback.lastModified).toLocaleString() }}</b>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
    <p v-else>No reviewer feedback submitted yet</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { useReviewEditorAPI } from "@/composables/api";
import type { ReviewerFeedback } from "@/types";

const props = defineProps<{
  reviewId: string;
  disabled: boolean;
}>();

const { listFeedback } = useReviewEditorAPI();

const feedbackItems = ref<ReviewerFeedback[]>([]);

const sortedFeedbackItems = computed(() => {
  return [...feedbackItems.value].sort((a, b) => {
    const ta = new Date(a.lastModified).getTime();
    const tb = new Date(b.lastModified).getTime();
    return tb - ta;
  });
});

onMounted(async () => {
  await retrieveFeedback();
});

async function retrieveFeedback() {
  const response = await listFeedback(props.reviewId);
  feedbackItems.value = response.data.results;
}

function recommendationVariant(rec?: ReviewerFeedback["recommendation"]): string {
  if (rec === "accept") return "success";
  if (rec === "revise") return "danger";
  return "gray";
}

function reviewStatusVariant(status?: ReviewerFeedback["reviewStatus"]): string {
  if (status === "Review is complete") return "success";
  if (status === "Awaiting editor feedback") return "warning";
  return "info";
}

function isLatestNonDraft(feedback: ReviewerFeedback): boolean {
  const latest = sortedFeedbackItems.value.find(f => f.recommendation);
  return latest === feedback;
}
</script>
