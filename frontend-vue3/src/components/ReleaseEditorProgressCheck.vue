<template>
  <div class="row mb-2">
    <div class="col-1">
      <i :class="iconClass"></i>
    </div>
    <div class="col-10">
      <slot name="label"> {{ label }}</slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useReleaseEditorStore } from "@/stores/releaseEditor";

const props = withDefaults(
  defineProps<{
    check: boolean;
    label?: string;
    optional?: boolean;
  }>(),
  {
    optional: false,
  }
);

const store = useReleaseEditorStore();

const iconClass = computed(() => {
  if (!store.isInitialized) {
    return "fas fa-circle-notch fa-spin text-muted";
  }
  if (props.optional && !props.check) {
    return "far fa-circle text-muted";
  }
  return props.check ? "fas fa-check-circle text-success" : "fas fa-times-circle text-danger";
});
</script>
