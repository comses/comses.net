<template>
  <div>
    <div v-if="error" class="d-block invalid-feedback">
      {{ error }}
    </div>
    <small v-if="help" class="form-text text-muted" :aria-describedby="idFor">
      {{ help }}
    </small>
  </div>
</template>

<script setup lang="ts">
export interface HelpErrorProps {
  idFor: string;
  help?: string;
  error?: string;
}

const props = defineProps<HelpErrorProps>();
</script>
