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
import { useFormField } from "@/composables/form";
import FormLabel from "@/components/form/FormLabel.vue";
import FormHelp from "@/components/form/FormHelp.vue";
import FormError from "@/components/form/FormError.vue";

export type Tags = { name: string }[];

export interface TextInputProps {
  name: string;
  label?: string;
  help?: string;
  placeholder?: string;
  required?: boolean;
}

const props = defineProps<TextInputProps>();

const { id, value, attrs, error } = useFormField(props, "name");

const matchingTags = ref<Tags>([]);
const isLoading = ref(false);

async function fetchMatchingTags(search: string) {
  // FIXME: temporary, should be in the requests API w/ axios
  isLoading.value = true;
  const response = await fetch(`/tags/?page=1&query=${search}&type=`);
  const data = await response.json();
  matchingTags.value = data.results;
  isLoading.value = false;
}

async function addTag(name: string) {
  (value as any).value.push({ name });
}
</script>
