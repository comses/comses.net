<template>
  <div>
    <label for="peer-reviewer-search" class="form-label" aria-labelledby="peer-reviewer-search">
      {{ label }}
    </label>
    <VueMultiSelect
      v-model="value"
      id="peer-reviewer-search"
      :multiple="false"
      track-by="id"
      label="id"
      :allow-empty="true"
      :options="matchingReviewers"
      :loading="isLoading"
      :searchable="true"
      :internal-search="false"
      :close-on-select="true"
      :options-limit="50"
      :limit="20"
      @search-change="fetchMatchingReviewers"
      @select="handleSelect"
    >
    <template #caret="{ toggle }">
        <div class="multiselect__search-toggle">
          <i class="fas fa-search" @mousedown.prevent.stop="toggle" />
        </div>
      </template>
      <template #option="{ option }">
        <b>{{ option.memberProfile.name }}</b>
        <small class="text-muted">{{ option.memberProfile.email }}</small>
        <small>{{ option.programmingLanguages }}</small>
      </template>
      <template #singleLabel="{ option }">
        <b>{{ option.memberProfile.name }}</b>
        <small class="text-muted">{{ option.memberProfile.email }}</small>
        <small>{{ option.programmingLanguages }}</small>
      </template>
      <template #noOptions>No matching users found.</template>
    </VueMultiSelect>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import VueMultiSelect from "vue-multiselect";
import { useDebounceFn } from "@vueuse/core";
import { useReviewEditorAPI } from "@/composables/api";
import type { Reviewer } from "@/types";

export interface UserSearchProps {
  modelValue?: Reviewer | null;
  label?: string;
  placeholder?: string;
}

const props = withDefaults(defineProps<UserSearchProps>(), {
  label: "Search for Peer Reviewers",
  placeholder: "",
});
const emit = defineEmits(["update:modelValue", "select"]);

const { findReviewers } = useReviewEditorAPI();

const matchingReviewers = ref<Reviewer[]>([]);
const isLoading = ref(false);

onMounted(async () => {
  await fetchMatchingReviewers("");
});

const value = computed({
  get() {
    return props.modelValue;
  },
  set(value) {
    emit("update:modelValue", value);
  },
});

const fetchMatchingReviewers = useDebounceFn(async (query: string) => {
    isLoading.value = true;
    try {
      const response = await findReviewers({ query });
      matchingReviewers.value = response.data.results;
    } catch (e) {
      // no-op
    } finally {
      isLoading.value = false;
    }
}, 600);

function handleSelect(selection: Reviewer) {
  emit("select", selection);
}
</script>
