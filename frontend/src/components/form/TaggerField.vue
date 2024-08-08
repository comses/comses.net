<template>
  <div>
    <slot name="label">
      <FieldLabel v-if="label" :label="label" :id-for="id" class="fw-bold" :required="required" />
    </slot>
    <FormPlaceholder v-if="showPlaceholder" />
    <VueMultiSelect
      v-else
      v-model="value"
      :id="id"
      v-bind="attrs"
      :multiple="true"
      track-by="name"
      label="name"
      :placeholder="placeholder"
      :options="matchingTags"
      :loading="isLoading"
      :searchable="true"
      :internal-search="false"
      :clear-on-select="false"
      :close-on-select="false"
      :options-limit="50"
      :taggable="true"
      :limit="20"
      @tag="addTag"
      @search-change="fetchMatchingTags"
      @select="attrs.onInput()"
      :class="{ 'is-invalid': error }"
    >
      <template #clear v-if="value?.length">
        <div class="multiselect__clear">
          <span @mousedown.prevent.stop="value = []">&times;</span>
        </div>
      </template>
      <template #caret="{ toggle }">
        <div :class="{ 'multiselect__search-toggle': true, 'd-none': value?.length }">
          <i class="fas fa-search" @mousedown.prevent.stop="toggle" />
        </div>
      </template>
      <template #noOptions>No matching tags found.</template>
    </VueMultiSelect>
    <slot name="help">
      <FieldHelp v-if="help" :help="help" :id-for="id" />
    </slot>
    <slot name="error">
      <FieldError v-if="error" :error="error" :id-for="id" />
    </slot>
  </div>
</template>

<script setup lang="ts">
import { ref, inject } from "vue";
import VueMultiSelect from "vue-multiselect";
import { useField } from "@/composables/form";
import FieldLabel from "@/components/form/FieldLabel.vue";
import FieldHelp from "@/components/form/FieldHelp.vue";
import FieldError from "@/components/form/FieldError.vue";
import FormPlaceholder from "@/components/form/FormPlaceholder.vue";
import { useTagsAPI } from "@/composables/api";
import type { Tag, TagType } from "@/types";

export interface TaggerFieldProps {
  // FIXME: extend from types/BaseFieldProps when vuejs/core#8083 makes it into a release
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  required?: boolean;
  type?: TagType;
}

const props = withDefaults(defineProps<TaggerFieldProps>(), {
  type: "",
  placeholder: "Type to add tags",
});

const { id, value, attrs, error } = useField<Tag[]>(props, "name");

const showPlaceholder = inject("showPlaceholder", false);

const matchingTags = ref<Tag[]>([]);
const isLoading = ref(false);

const { search } = useTagsAPI();

async function fetchMatchingTags(query: string) {
  isLoading.value = true;
  const response = await search({ query, type: props.type });
  matchingTags.value = response.data.results;
  isLoading.value = false;
}

async function addTag(name: string) {
  value.value.push({ name });
}
</script>
