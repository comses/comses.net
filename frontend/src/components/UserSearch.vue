<template>
  <div>
    <label v-if="label" class="form-label" for="reviewer-search">
      {{ label }}
    </label>
    <VueMultiSelect
      v-model="value"
      id="user-search"
      :multiple="false"
      track-by="id"
      label="id"
      :placeholder="placeholder"
      :allow-empty="true"
      :options="matchingUsers"
      :loading="isLoading"
      :searchable="true"
      :internal-search="false"
      :close-on-select="true"
      :options-limit="50"
      :limit="20"
      @search-change="fetchMatchingUsers"
      @select="handleSelect"
      :disabled="disabled"
    >
      <template #clear v-if="value">
        <div class="multiselect__clear">
          <span @mousedown.prevent.stop="value = null">&times;</span>
        </div>
      </template>
      <template #caret="{ toggle }">
        <div :class="{ 'multiselect__search-toggle': true, 'd-none': !!value }">
          <i class="fas fa-search" @mousedown.prevent.stop="toggle" />
        </div>
      </template>
      <template #option="{ option }">
        <div class="d-flex flex-row">
          <div v-if="showAvatar" style="width: 3rem; height: 3rem">
            <img
              v-if="option.avatarUrl"
              :src="option.avatarUrl"
              class="d-block img-fluid img-thumbnail"
            />
            <div v-else class="img-thumbnail w-100 h-100"></div>
          </div>
          <div class="d-flex flex-column justify-content-center ms-3">
            <div class="mb-1">
              <b>{{ option.name }}</b>
              <a v-if="showLink" :href="option.profileUrl" target="_blank"
                ><small class="fas fa-link ms-1"></small
              ></a>
              <small v-if="showEmail && option.email" class="text-muted">
                ({{ option.email }})</small
              >
              <small v-if="showAffiliation && option.primaryAffiliationName"
                >, {{ option.primaryAffiliationName }}</small
              >
            </div>
            <div v-if="showTags" class="tag-list">
              <div class="tag" v-for="tag in option.tags" :key="tag.name">
                {{ tag.name }}
              </div>
            </div>
          </div>
        </div>
      </template>
      <template #selection=""></template>
      <template #noOptions>No results found.</template>
      <template #noResult v-if="errors && errors.length > 0">
        Unable to fetch matching users. Check your connection or try again later.
        <div class="mt-2 text-danger">
          <small>{{ errors.join(", ") }}</small>
        </div>
      </template>
    </VueMultiSelect>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import VueMultiSelect from "vue-multiselect";
import { useDebounceFn } from "@vueuse/core";
import type { AxiosResponse } from "axios";
import type { UserSearchQueryParams, RelatedMemberProfile } from "@/types";

export interface UserSearchProps {
  modelValue?: RelatedMemberProfile | null;
  label?: string;
  placeholder?: string;
  showAffiliation?: boolean;
  showAvatar?: boolean;
  showEmail?: boolean;
  showTags?: boolean;
  showLink?: boolean;
  searchFn: (
    params: UserSearchQueryParams
  ) => Promise<AxiosResponse<{ results: RelatedMemberProfile[] }, any>>;
  errors?: string[];
  disabled?: boolean;
}

const props = withDefaults(defineProps<UserSearchProps>(), {
  label: "Search for a CoMSES Net User",
  placeholder: "",
  showAffiliation: false,
  showAvatar: true,
  showEmail: false,
  showTags: false,
  showLink: false,
});
const emit = defineEmits(["update:modelValue", "select"]);

const matchingUsers = ref<RelatedMemberProfile[]>([]);
const isLoading = ref(false);

const value = computed({
  get() {
    return props.modelValue;
  },
  set(value) {
    emit("update:modelValue", value);
  },
});

const fetchMatchingUsers = useDebounceFn(async (query: string) => {
  if (query) {
    isLoading.value = true;
    try {
      const response = await props.searchFn({ query });
      matchingUsers.value = response.data.results;
    } catch (e) {
      // no-op
    } finally {
      isLoading.value = false;
    }
  }
}, 600);

function handleSelect(selection: RelatedMemberProfile) {
  emit("select", selection);
}
</script>
