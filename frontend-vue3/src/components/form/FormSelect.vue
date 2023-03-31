<template>
  <div>
    <slot name="label">
      <FormLabel :label="label" :id-for="id" :required="required"></FormLabel>
    </slot>
    <select
      v-model="value"
      :id="id"
      v-bind="attrs"
      :class="{ 'form-select': true, 'is-invalid': error }"
    >
      <option v-for="option in options" :key="option.value" :value="option.value">
        {{ option.label }}
      </option>
    </select>
    <FormHelpErrors :help="help" :id-for="id" :error="error"></FormHelpErrors>
  </div>
</template>

<script setup lang="ts">
import { useFormField } from "@/composables/formfield";
import FormLabel from "@/components/form/FormLabel.vue";
import FormHelpErrors from "@/components/form/FormHelpErrors.vue";

export type SelectOptions = { value: any; label: string }[];

export interface TextInputProps {
  name: string;
  label: string;
  help?: string;
  required?: boolean;
  options: SelectOptions;
}

const props = defineProps<TextInputProps>();

const { id, value, attrs, error } = useFormField(props, "name");
</script>
