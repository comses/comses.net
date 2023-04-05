<template>
  <div>
    <a class="text-white" :href="submitUrl">
      <div class="btn btn-secondary w-100" tabindex="0">
        {{ submitLabel }}
      </div>
    </a>
    <slot name="form"></slot>
    <a class="text-white" :href="searchUrl">
      <div class="btn btn-primary w-100" tabindex="0">
        {{ searchLabel }}
      </div>
    </a>
  </div>
</template>
<script setup lang="ts">
export interface SearchProps {
  submitLabel: string;
  submitUrl: string;
  searchLabel: string;
  searchUrl: string;
}

const props = defineProps<SearchProps>();
</script>
