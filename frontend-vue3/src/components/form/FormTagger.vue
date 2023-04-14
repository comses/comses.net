<template>
  <div>
    <slot name="label">
      <FormLabel v-if="label" :label="label" :id-for="id" :required="indicateRequired" />
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
      <FormHelp v-if="help" :help="help" :id-for="id" />
    </slot>
    <slot name="error">
      <FormError v-if="error" :error="error" :id-for="id" />
    </slot>
  </div>
</template>

<script setup lang="ts">
import { ref, onBeforeMount, inject } from "vue";
import VueMultiSelect from "vue-multiselect";
import { useField } from "@/composables/form";
import FormLabel from "@/components/form/FormLabel.vue";
import FormHelp from "@/components/form/FormHelp.vue";
import FormError from "@/components/form/FormError.vue";
import FormPlaceholder from "@/components/form/FormPlaceholder.vue";
import { useTagsAPI } from "@/composables/api/tags";
import type { Tags, TagType } from "@/composables/api/tags";

export interface TaggerProps {
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  indicateRequired?: boolean;
  type?: TagType;
}

const props = withDefaults(defineProps<TaggerProps>(), {
  type: "",
  placeholder: "Type to add tags",
});

const { id, value, attrs, error } = useField<Tags>(props, "name");

const showPlaceholder = inject("showPlaceholder", false);

const matchingTags = ref<Tags>([]);
const isLoading = ref(false);

const { search } = useTagsAPI();

onBeforeMount(() => {
  // force the inital value to be an empty array
  value.value = [];
});

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
