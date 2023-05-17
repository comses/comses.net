<template>
  <div class="row">
    <div class="col-sm-12 col-md-8">
      <ReviewInvitations :review-id="reviewId" @pollEvents="retrieveEvents" />
      <h2 class="mt-4">Feedback</h2>
      <ReviewFeedback :review-id="reviewId" />
    </div>
    <div class="col-sm-12 col-md-4">
      <ReviewEventLog :events="events" :errors="eventErrors" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import ReviewInvitations from "@/components/ReviewInvitations.vue";
import ReviewFeedback from "@/components/ReviewFeedback.vue";
import ReviewEventLog from "@/components/ReviewEventLog.vue";
import { useReviewEditorAPI } from "@/composables/api";

export interface ReviewEditorProps {
  reviewId: string;
  statusLevels: { value: string; label: string }[];
  status: string;
}

const props = defineProps<ReviewEditorProps>();

const { data: events, serverErrors: eventErrors, listEvents } = useReviewEditorAPI();

onMounted(async () => {
  await retrieveEvents();
});

async function retrieveEvents() {
  await listEvents(props.reviewId);
}
</script>
