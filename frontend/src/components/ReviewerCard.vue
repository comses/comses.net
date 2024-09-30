<template>
  <div class="card mb-3">
    <div class="card-header">
      <h5 class="card-title">
        {{ reviewer.memberProfile.name }} ({{ reviewer.memberProfile.username }})
      </h5>
    </div>
    <div class="card-body">
      <p class="card-text">
        <strong>Email:</strong> {{ reviewer.memberProfile.email }}<br />
        <strong>Programming Languages:</strong> {{ reviewer.programmingLanguages.join(", ") }}<br />
        <strong>Subject Areas:</strong> {{ reviewer.subjectAreas.join(", ") }}<br />
        {{ reviewer.notes }}
      </p>
      <a class="btn btn-primary me-1" @click="emit('edit')">Edit</a>
      <a v-if="reviewer.isActive" class="btn btn-danger" @click="changeActiveState(reviewer, false)"
        >Deactivate</a
      >
      <a v-else class="btn btn-success" @click="changeActiveState(reviewer, true)">Activate</a>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Reviewer } from "@/types";
import { useReviewEditorAPI } from "@/composables/api";

const props = defineProps<{ reviewer: Reviewer }>();
const emit = defineEmits<{
  edit: [];
  changeActiveState: [Reviewer];
}>();

const { updateReviewer: update } = useReviewEditorAPI();

async function changeActiveState(reviewer: Reviewer, isActive: boolean) {
  // FIXME: Make server accept partial reviewer object without defining memberProfileId
  const response = await update(reviewer.id, {
    memberProfileId: reviewer.memberProfile.id,
    isActive,
  });
  emit("changeActiveState", response.data);
}
</script>
