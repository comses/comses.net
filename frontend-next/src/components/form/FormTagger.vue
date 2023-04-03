<template>
  <div>
    <slot name= "label">
      <FormLabel :label="label" :id-for="id" :required="required"></FormLabel>
    </slot>
    <VueMultiSelect
      v-model="value"
      :id="id"
      v-bind="attrs"
      :multiple="true"
      track-by="name"
      :options="matchingTags"
      :loading="isLoading"
      :searchable="true"
      :internal-search="false"
      :clear-on-select="false"
      :close-on-select="false"
      :options-limit="50"
      :limit="20"
      @tag="addTag"
      @search-change="fetchMatchingTags"
      :class="{ 'is-invalid': error }"
    ></VueMultiSelect>
    <FormHelpErrors :help="help" :id-for="id" :error="error"></FormHelpErrors>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import VueMultiSelect from "vue-multiselect"
import { useFormField } from "@/composables/formfield";
import FormLabel from "@/components/form/FormLabel.vue";
import FormHelpErrors from "@/components/form/FormHelpErrors.vue";

export type Tags = { name: string }[];

export interface TextInputProps {
  name: string;
  label: string;
  help?: string;
  required?: boolean;
}

const props = defineProps<TextInputProps>();

const { id, value, attrs, error } = useFormField(props, "name");

const matchingTags = ref<Tags>([]);
const isLoading = ref(false);

async function fetchMatchingTags(search: string) {
  // FIXME: temporary, should be in the requests API w/ axios
  isLoading.value = true;
  const response = await fetch(`/api/tags?search=${search}`); // add type param
  const data = await response.json();
  matchingTags.value = data.results;
  isLoading.value = false;
}

async function addTag(name: string) {

}
</script>
