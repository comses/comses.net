<template>
  <div>
    <label class="form-label" for="reviewer-search">
      Search by name, email address, or username among existing CoMSES Net members
    </label>
    <VueMultiSelect
      v-model="value"
      id="reviewer-search"
      :multiple="false"
      track-by="username"
      label="username"
      placeholder="Find a reviewer"
      :allow-empty="true"
      :options="matchingUsers"
      :loading="isLoading"
      :searchable="true"
      :internal-search="false"
      :close-on-select="true"
      :options-limit="50"
      :limit="20"
      @search-change="fetchMatchingUsers"
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
        <div class="container">
          <div class="row">
            <div class="col-2">
              <img
                :src="option.avatar_url"
                alt="No picture available"
                class="d-block img-fluid img-thumbnail"
              />
            </div>
            <div class="col-10">
              <div class="col-10">
                <h2>{{ option.name }}</h2>
                <div class="tag-list">
                  <div class="tag mx-1" v-for="tag in option.tags" :key="tag.name">
                    {{ tag.name }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
      <template #noOptions>No results found.</template>
      <template #noResult v-if="serverErrors.length > 0">
        Unable to fetch matching users. Check your connection or try again later.
        <div class="mt-2 text-danger">
          <small>{{ serverErrors.join(", ") }}</small>
        </div>
      </template>
    </VueMultiSelect>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import VueMultiSelect from "vue-multiselect";
import { useDebounceFn } from "@vueuse/core";
import { useReviewEditorAPI } from "@/composables/api/revieweditor";

const props = defineProps(["modelValue"]);
const emit = defineEmits(["update:modelValue"]);

const matchingUsers = ref<any[]>([]);
const isLoading = ref(false);

const { serverErrors, findReviewers } = useReviewEditorAPI();

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
      const response = await findReviewers(query);
      matchingUsers.value = response.data.results;
    } catch (e) {
      // no-op
    } finally {
      isLoading.value = false;
    }
  }
}, 600);
</script>
