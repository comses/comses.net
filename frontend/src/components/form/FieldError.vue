<template>
  <div class="d-block invalid-feedback">
    {{ error }}
  </div>
</template>

<script setup lang="ts">
export interface ErrorProps {
  error?: string;
}

const props = defineProps<ErrorProps>();
</script>
