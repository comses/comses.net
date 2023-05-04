<template>
  <small class="form-text text-muted" :aria-describedby="idFor">
    {{ help }}
  </small>
</template>

<script setup lang="ts">
export interface HelpProps {
  idFor: string;
  help?: string;
}

const props = defineProps<HelpProps>();
</script>
