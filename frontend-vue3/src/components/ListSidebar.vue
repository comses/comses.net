<template>
  <div class="">
    <a v-if="createUrl && createLabel" class="text-white" :href="createUrl">
      <div class="btn btn-secondary w-100" tabindex="0">
        {{ createLabel }}
      </div>
    </a>
    <div class="card-metadata">
      <h2 class="title">Refine Search</h2>
      <div class="card-body">
        <slot name="form" />
      </div>
    </div>
    <a class="text-white" :href="searchUrl">
      <div class="btn btn-primary w-100" tabindex="0">
        {{ searchLabel }}
      </div>
    </a>
  </div>
</template>
<script setup lang="ts">
export interface SearchProps {
  createLabel?: string;
  createUrl?: string;
  searchLabel: string;
  searchUrl: string;
}

const props = defineProps<SearchProps>();
</script>
