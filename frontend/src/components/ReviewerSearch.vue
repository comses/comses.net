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
        <div class="d-flex flex-row">
          <div style="width: 3rem; height: 3rem">
            <img
              v-if="option.avatarUrl"
              :src="option.avatarUrl"
              class="d-block img-fluid img-thumbnail"
            />
            <div v-else class="img-thumbnail w-100 h-100"></div>
          </div>
          <div class="d-flex flex-column justify-content-center ms-3">
            <div class="mb-1">
              <b>{{ option.memberProfile.name }}</b>
              <small v-if="option.memberProfile.email" class="text-muted">
                ({{ option.memberProfile.email }})</small
              >
            </div>
          </div>
        </div>
        <div class="d-flex flex-row">
          <div class="d-flex flex-column justify-content-center ms-5">
            <div class="ms-1 mb-1">
              <span v-if="option.programmingLanguages"
                >Programming Lanugages: {{ option.programmingLanguages.join(", ") }}</span
              >
            </div>
          </div>
        </div>
        <div class="d-flex flex-row">
          <div class="d-flex flex-column justify-content-center ms-5">
            <div class="ms-1 mb-1">
              <span v-if="option.subjectAreas"
                >Subject Areas: {{ option.subjectAreas.join(", ") }}</span
              >
            </div>
          </div>
        </div>
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
