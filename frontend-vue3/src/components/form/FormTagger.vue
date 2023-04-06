<template>
  <div>
    <slot name= "label">
      <FormLabel v-if="label" :label="label" :id-for="id" :required="required" />
    </slot>
    <VueMultiSelect
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
    ></VueMultiSelect>
    <slot name="help">
      <FormHelp v-if="help" :help="help" :id-for="id" :error="error" />
    </slot>
    <slot name="error">
      <FormError v-if="error" :error="error" :id-for="id" />
    </slot>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import VueMultiSelect from "vue-multiselect"
import { useField } from "@/composables/form";
import FormLabel from "@/components/form/FormLabel.vue";
import FormHelp from "@/components/form/FormHelp.vue";
import FormError from "@/components/form/FormError.vue";
import { useTagsAPI } from "@/composables/api/tags";
import type { Tags } from "@/composables/api/tags";

export interface TextInputProps {
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  required?: boolean;
  type?: "" | "Event" | "Codebase" | "Job" | "Profile";
}

const props = withDefaults(defineProps<TextInputProps>(), {
  type: "",
  placeholder: "Type to add tags",
});

const { id, value, attrs, error } = useField(props, "name");

const matchingTags = ref<Tags>([]);
const isLoading = ref(false);

const { list } = useTagsAPI();

async function fetchMatchingTags(search: string) {
  isLoading.value = true;
  const response = await list(search, props.type);
  matchingTags.value = response.data.results;
  isLoading.value = false;
}

async function addTag(name: string) {
  (value as any).value.push({ name });
}
</script>
