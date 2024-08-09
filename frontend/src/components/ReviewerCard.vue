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
      <a v-if="reviewer.isActive" class="btn btn-danger" @click="emit('deactivate')">Deactivate</a>
      <a v-else class="btn btn-success" @click="emit('activate')">Activate</a>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Reviewer } from "@/types";

const props = defineProps<{ reviewer: Reviewer }>();
const emit = defineEmits(["edit", "activate", "deactivate"]);
</script>
