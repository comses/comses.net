<template>
  <div class="d-flex align-items-center">
    <label
      for="select-sort-by"
      aria-labelledby="select-sort-by"
      class="form-label text-nowrap mb-0 me-2"
    >
      Sort by
    </label>
    <select
      v-model="selectedOrdering"
      id="select-sort-by"
      class="form-select"
      @change="handleChange"
    >
      <option v-for="option in props.sortOptions" :key="option.value" :value="option.value">
        {{ option.label }}
      </option>
    </select>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";

export interface SortByProps {
  sortOptions: { value: string; label: string }[];
}

const props = defineProps<SortByProps>();

const selectedOrdering = ref("");

onMounted(() => {
  const url = new URL(window.location.href);
  let initialOrdering = "";

  if (url.pathname.includes("codebases")) {
    // special case for model library: initial load should sort by latest published
    // if given a bare query with no ordering, sort by relevance
    if (url.searchParams.get("query")) {
      initialOrdering = "relevance";
    } else {
      // FIXME: should probably remove "Relevance" if there's no query as it doesn't really make sense to sort by
      // "relevance" when there's no criteria in play
      initialOrdering = "-first_published_at";
    }
  }
  selectedOrdering.value = url.searchParams.get("ordering") || initialOrdering;
});

function handleChange() {
  const url = new URL(window.location.href);
  if (selectedOrdering.value === "") {
    url.searchParams.delete("ordering");
  } else {
    url.searchParams.set("ordering", selectedOrdering.value);
  }
  window.location.href = url.toString();
}
</script>
