<template>
  <div class="">
    <a v-if="createUrl && createLabel" class="text-white" :href="createUrl">
      <div class="btn btn-secondary w-100" tabindex="0">
        {{ createLabel }}
      </div>
    </a>
    <div class="card-metadata">
      <h2 class="title fw-bold">Refine Search</h2>
      <div class="card-body">
        <slot name="form" />
      </div>
    </div>
    <a class="text-white" :href="searchUrl">
      <div
        :class="{ disabled: isApplyingFiltersLoading }"
        class="btn btn-primary w-100"
        tabindex="0"
        v-on:click="isApplyingFiltersLoading = true"
      >
        <span v-if="isApplyingFiltersLoading">
          <i class="fas fa-spinner fa-spin me-1"></i>Applying Filters</span
        >
        <span v-else>{{ searchLabel }}</span>
      </div>
    </a>

    <button
      v-if="clearAllFilters"
      type="button"
      :class="{ disabled: isClearingFiltersLoading }"
      class="btn btn-secondary mt-2 w-100"
      v-on:click="isClearingFiltersLoading = true"
      @click="clearAllFilters"
    >
      <span v-if="isClearingFiltersLoading">
        <i class="fas fa-spinner fa-spin me-1"></i>Clearing Filters</span
      >
      <span v-else>Clear Filters</span>
    </button>
  </div>
</template>
<script setup lang="ts">
import { ref } from "vue";

const isApplyingFiltersLoading = ref(false);
const isClearingFiltersLoading = ref(false);

export interface SearchProps {
  createLabel?: string;
  createUrl?: string;
  searchLabel: string;
  searchUrl: string;
  clearAllFilters?: () => void;
}

const props = defineProps<SearchProps>();
</script>
