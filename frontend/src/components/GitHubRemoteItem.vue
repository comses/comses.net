<template>
  <a :href="remote.url" target="_blank">{{ remote.owner }}/{{ remote.repoName }}</a>
  <span v-if="remote.isActive" class="badge bg-success">active</span>
  <span v-else class="badge bg-gray">inactive</span>
</template>

<script setup lang="ts">
import type { CodebaseGitRemote } from "@/types";

const props = defineProps<{
  remote: CodebaseGitRemote;
}>();
</script>
