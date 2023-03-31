<template>
  <label :for="idFor" class="form-label" :aria-labelledby="idFor">
    {{ label }}
    <span v-if="required" class="text-danger">*</span>
  </label>
</template>

<script setup lang="ts">
/**
 * 
 */
export interface LabelProps {
  label: string;
  idFor: string;
  required?: boolean;
}

const props = withDefaults(defineProps<LabelProps>(), {
  required: false,
});
</script>
