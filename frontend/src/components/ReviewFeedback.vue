<template>
  <div>
    <div class="container-fluid px-0" v-if="feedbackItems && feedbackItems.length > 0">
      <div class="row" v-for="feedback in feedbackItems" :key="feedback.dateCreated">
        <div class="col-xs-12 col-sm-6">
          <a :href="feedback.editorUrl">
            {{ feedback.reviewerName }} recommended: <mark>{{ feedback.recommendation }}</mark>
          </a>
        </div>
        <div class="col-xs-12 col-sm-6">
          <span class="badge bg-info"
            >{{ feedback.reviewStatus }} as of
            {{ new Date(feedback.dateCreated).toDateString() }}</span
          >
        </div>
      </div>
    </div>
    <p v-else>No reviewer feedback submitted yet</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useReviewEditorAPI } from "@/composables/api";

const props = defineProps<{
  reviewId: string;
}>();

const { listFeedback } = useReviewEditorAPI();

const feedbackItems = ref<any[]>([]);

onMounted(async () => {
  await retrieveFeedback();
});

async function retrieveFeedback() {
  const response = await listFeedback(props.reviewId);
  feedbackItems.value = response.data.results;
}
</script>
